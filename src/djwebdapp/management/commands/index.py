import asyncio
import multiprocessing
import os
import sys
import time

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.models import Q
from django.utils import timezone

from djwebdapp.models import Blockchain


def get_blockchain(name_or_id):
    return Blockchain.objects.get(Q(name=name_or_id) | Q(id=name_or_id))


class Worker(multiprocessing.Process):
    def __init__(self, queue, blockchain, endpoint, done, stop):
        super().__init__()
        self.queue = queue
        self.blockchain = blockchain
        self.endpoint = endpoint
        self.done = done
        self.stop = stop

    def run(self):
        self.blockchain = get_blockchain(self.blockchain)
        main_node = self.blockchain.node_set.filter(
            endpoint=self.endpoint
        ).first()
        other_nodes = self.blockchain.node_set.filter(
            is_active=True
        ).exclude(
            endpoint=self.endpoint
        ).order_by(
            '-priority'
        )
        nodes = [main_node] + list(other_nodes)
        provider = self.blockchain.provider
        provider.node = main_node
        provider.index_init()

        for level in iter(self.queue.get, None):
            if self.stop.is_set():
                return

            try:
                print(f'Indexing {level} from {provider.node.endpoint}')
                provider.index_level(level)
                indexed_at = timezone.now()
                print(f'Indexed {level}')
            except KeyboardInterrupt:
                return
            except:
                # we couldn't index this level with any node, let's try
                # again later and hope for the best
                print(f'Failed {level} on all nodes, re-queuing')
                self.queue.put(level)
            else:
                self.indexed_block(level, indexed_at)
                # check if done every N blocks
                if not level % 30:  
                    print(f'Checking for remaining contracts to index')
                    if not self.blockchain.remaining():
                        print(f'No more contracts to index')
                        self.done.set()
                        return

    def indexed_block(self, level, indexed_at):
        # not sure if update_or_create would be blocking the table with a
        # SELECT FOR UPDATE and we need to write a lot on that table
        # to be able to support indexation resuming in case of reboot
        block = self.blockchain.block_set.filter(
            level=level
        ).first()
        if block:
            block.indexed_at = timezone.now()
            block.save()
        else:
            self.blockchain.block_set.create(
                level=level,
                indexed_at=indexed_at,
            )


class Command(BaseCommand):
    """
    Doing a lot of dance here so that:

    - running without arguments continously runs indexers for all blockchains
      in parallel
    - running with a blockchain arguments and without a workers argument
      replaces the process with worker arguments from the configuration in the
      database
    - finnaly, we are able to spawn workers *before* issuing any database
      connection so that each worker can have their own

    This is because multiprocessing forks the process which copies all file
    handlers including the database connection which we need to avoid to enjoy
    a fully functionnal db connection per process.
    """

    help = 'Synchronize external transactions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--blockchain', 
            type=str,
            help='Blockchain name or ID',
        )
        parser.add_argument(
            'workers', 
            nargs='*',
            type=str,
            help='Workers in the form of endpoint=num_processes',
        )

    def handle(self, *args, **options):
        if options['blockchain']:
            if not options['workers']:
                args = [
                    sys.argv[0],
                    'index',
                    '--blockchain=' + options['blockchain'],
                ] + self.workers_option_generate(options['blockchain'])
                print(f'Replacing myself with: {" ".join(args)}')
                os.execvp(sys.argv[0], args)

            try:
                self.handle_blockchain(options['blockchain'], options['workers'])
            except KeyboardInterrupt:
                self.stop.set()
                for worker in self.workers:
                    worker.join(3)
                    worker.terminate()
                raise
        else:
            self.handle_blockchains()

    def handle_blockchains(self):
        async def run(cmd):
            while True:
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                )
                stdout, stderr = await proc.communicate()
                await asyncio.sleep(10)  # arbitrary wait
        
        blockchains = list(Blockchain.objects.filter(is_active=True))
        connections.close_all()  # we won't need the db anymore

        runs = [
            run(f'./manage.py index --blockchain {blockchain.id}')
            for blockchain in blockchains
        ]

        async def run_all():
            await asyncio.gather(*runs)

        asyncio.run(run_all())

    def workers_option_generate(self, blockchain):
        nodes = get_blockchain(blockchain).node_set.filter(
            is_active=True
        ).order_by('-priority')

        workers = []
        for node in nodes:
            workers.append(f'{node.endpoint}={node.workers}')
        return workers

    def handle_blockchain(self, blockchain, workers):
        # We'll be pushing levels to index in here
        queue = multiprocessing.Queue()
        # A worker that figures we don't have any remaining contract to find
        # will set this
        done = multiprocessing.Event()
        # When done is set, we'll set stop to stop all ongoing workers
        self.stop = multiprocessing.Event()

        # we need to start multiprocessing workers before connecting to the
        # database
        self.workers = []
        for worker_data in workers:
            endpoint, number = worker_data.split('=')
            for i in range(int(number)):
                worker = Worker(
                    queue,
                    blockchain,
                    endpoint,
                    done,
                    self.stop,
                )
                worker.start()
                self.workers.append(worker)
        print('Started workers')

        # now that we've started the workers, we may use the database
        blockchain = get_blockchain(blockchain)
        remaining = blockchain.remaining()

        reorg = (
            blockchain.max_level
            and start_level < blockchain.max_level
        )
        if reorg:
            print(f'RE-ORG from {start_level}')

            # cancel all transactions that were re-orged, those we have wallets
            # for will be re-spooled, the others are not our problem
            Transaction.objects.filter(
                sender__blockchain=blockchain,
                level__gte=blockchain.max_level,
            ).exclude(level=None).update(
                level=None,
                hash=None,
                address=None,
                state='deleted',
            )

            blockchain.max_level = blockchain.max_level
            blockchain.save()

            return  # let's not deal with this anymore in this process

        # let's always start from where we're at
        start_level = blockchain.head

        if blockchain.max_level and not remaining:
            # let's just index new blocks as we don't have any new contracts to
            # index in the past
            for level in range(blockchain.max_level - 1, start_level):
                # we did max_level-1 in case the last indexed block was not
                # finished at the time of indexation
                queue.put(level)
        else:
            # we're looking for contract originations in the past!
            # we might have to index a *lot* of blocks, ie. 20k or something
            # we do *not* want to re-index any block that has been indexed
            # since we added the last contract we need to find origination for
            most_recent_contract_to_index = blockchain.remaining().order_by(
                '-created_at'
            ).first()
            indexed = blockchain.block_set.filter(
                indexed_at__gt=most_recent_contract_to_index.created_at
            ).values_list('level', flat=True)

            current_level = start_level = blockchain.head
            while current_level:
                while queue.qsize() > len(self.workers) * 1.2:
                    # We don't need too many pending blocks per worker...
                    # However, a worker may enque a block it can't index, and
                    # we want that block to be retried in less than 3 block index,
                    # so we don't want to pile new levels until those are in
                    # planned in the near-future
                    time.sleep(1)

                if current_level not in indexed:
                    print(f'QUEUED {current_level}')
                    queue.put(current_level)

                current_level -= 1

            for worker in self.workers:
                # break iteration in Worker.run's iter of queue by putting None...
                queue.put(None)

            # ... although we're really hoping for a worker to set done
            done.wait()
            # we can now self.stop all workers
            self.stop.set()

        for worker in self.workers:
            worker.join()

        blockchain.max_level = start_level
        blockchain.save()
