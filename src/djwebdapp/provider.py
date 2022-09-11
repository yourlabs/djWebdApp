from multiprocessing import get_context
import random

from django import db
from django.db.models import Q

from djwebdapp.models import Transaction
from djwebdapp.signals import get_args


def call_deploy(arg):
    logger, call = arg

    logger.debug(f'starting {call} ...')
    try:
        call.deploy()
    except Exception:
        logger.exception(f'failed {call}')
    else:
        logger.info(f'success {call}')

    return call


def get_calls_distinct_sender(calls_query_set, n_calls):
    senders = set()
    distinct_calls = []
    for call in calls_query_set:
        if call.sender not in senders and len(distinct_calls) < n_calls:
            distinct_calls.append(call)
            senders.add(call.sender)

    return distinct_calls


class Provider:
    exclude_states = (
        'held', 'aborted', 'import', 'importing', 'watching', 'done'
    )
    spool_states = (
        'deleted',
        'deploy',
        'retrying',
    )

    def __init__(self, blockchain=None, wallet=None):
        self.wallet = wallet
        self.blockchain = wallet.blockchain if wallet else blockchain

    def download(self, target):
        """ Download a contract history from the configured indexer. """
        raise NotImplementedError()

    def index_level(self, level):
        raise NotImplementedError()

    def get_client(self, wallet=None):
        raise NotImplementedError()

    def get_args(self, transaction):
        results = get_args.send(
            sender=type(self),
            transaction=transaction,
        )
        for callback, result in results:
            if result:
                return result
        return transaction.args

    @property
    def client(self):
        cached = getattr(self, '_client', None)
        if cached:
            return cached
        self._client = self.get_client()
        return self._client

    @client.setter
    def client(self, value):
        self._client = value

    def index_init(self):
        self.hashes = self.transaction_class.objects.filter(
            blockchain=self.blockchain
        ).filter(
            Q(state='confirm') | ~Q(hash=None)
        ).values_list('hash', flat=True)
        self.logger.info(f'Found {len(self.hashes)} transactions to index')

        self.contracts = self.transaction_class.objects.filter(
            blockchain=self.blockchain,
            index=True,
            kind='contract',
        ).filter(
            Q(state='confirm') | ~Q(address=None),
        ).filter(
        )
        print(f'Found {len(self.contracts)} contracts to index')

        self.addresses = self.contracts.values_list(
            'address',
            flat=True,
        )
        self.logger.info(f'Found {len(self.addresses)} addresses to index')

    def deploy(self, transaction):
        raise NotImplementedError()

    def index(self):
        start_level = current_level = (
            self.head - self.blockchain.min_confirmations + 1
        )

        reorg = (
            self.blockchain.max_level
            and current_level < self.blockchain.max_level
        )
        if reorg:
            self.logger.warning(
                f'Detected reorg in {self.blockchain} '
                f'from {self.blockchain.max_level} to {start_level}'
            )
            # reorg
            Transaction.objects.filter(
                sender__blockchain=self.blockchain,
                level__gte=current_level,
            ).exclude(level=None).update(
                level=None,
                hash=None,
                address=None,
                state='deleted',
            )
            self.blockchain.max_level = current_level
            self.blockchain.save()
            return  # commit to reorg in a transaction

        fresh = (
            self.blockchain.max_level
            and start_level == self.blockchain.max_level
        )
        if fresh:
            # no need to go all way back further if we are up to date just
            # check the head
            max_depth = 1

        resume = (
            self.blockchain.max_level
            and start_level > self.blockchain.max_level
        )
        if resume:
            # go all way back to where we left
            max_depth = start_level - self.blockchain.max_level
            # last block was maybe not complete at the time of indexation:
            # compensate start level by adding one block
            max_depth += 1

        if not self.blockchain.max_level:
            # go with an arbitrary backlog
            max_depth = 500

        self.index_init()

        while current_level and start_level - current_level < max_depth:
            self.logger.debug(f'Indexing level {current_level}')
            self.index_level(current_level)
            current_level -= 1

        self.blockchain.max_level = start_level
        self.blockchain.save()

    def contracts(self):
        return self.transaction_class.objects.filter(
            blockchain=self.blockchain,
            kind='contract',
            hash=None,
            sender__blockchain__is_active=True,
            has_code=True,
        ).filter(
            Q(address='')
            | Q(address=None)
        ).filter(
            Q(sender__last_level__lt=self.head)
            | Q(sender__last_level=None)
        ).exclude(
            Q(sender__balance=None)
            | Q(sender__balance=0)
            | Q(state__in=self.exclude_states)
        ).select_related(
            'blockchain'
        ).order_by(
            'created_at'
        )

    def calls(self):
        return self.transaction_class.objects.filter(
            blockchain=self.blockchain,
            kind='function',
            hash=None,
            sender__blockchain__is_active=True,
        ).filter(
            Q(sender__last_level__lt=self.head)
            | Q(sender__last_level__isnull=True)
        ).exclude(
            Q(sender__balance=None)
            | Q(sender__balance=0)
            | Q(state__in=self.exclude_states)
            | Q(contract__address='')
            | Q(contract__address__isnull=True)
        ).select_related(
            'blockchain'
        ).order_by(
            'created_at'
        )

    def transfers(self):
        return self.transaction_class.objects.filter(
            blockchain=self.blockchain,
            kind='transfer',
            hash=None,
            sender__blockchain__is_active=True,
            sender__last_level__lt=self.head,
        ).exclude(
            Q(sender__balance=None)
            | Q(sender__balance=0)
            | Q(state__in=self.exclude_states)
        ).select_related(
            'blockchain'
        ).order_by(
            'created_at'
        )

    def spool(self):
        # senders which have already deployed during this block must be
        # excluded
        # is there any new transfer to deploy from an account with balance?
        transfer = self.transfers().filter(last_fail=None).first()
        if transfer:
            self.logger.info(f'Deploying transfer {transfer}')
            return transfer.deploy()
        self.logger.info('Found 0 transfers to deploy')

        # is there any new contract to deploy from an account with balance?
        contract = self.contracts().filter(last_fail=None).first()

        if contract:
            self.logger.info(f'Deploying contract {contract}')
            contract.deploy()
            return contract
        self.logger.info('Found 0 contracts to deploy')

        n_calls = 15
        calls = self.calls().filter(last_fail=None)
        distinct_calls = get_calls_distinct_sender(calls, n_calls)

        if distinct_calls:
            db.connections.close_all()
            pool = get_context("fork").Pool(n_calls)
            results = pool.map(
                call_deploy,
                [(self.logger, call) for call in list(distinct_calls)]
            )
            for result in results:
                result.save()

            if len(distinct_calls) == 1:
                return distinct_calls[0]
            else:
                return distinct_calls
        self.logger.info('Found 0 calls to send')

        # is there any transfer to retry from an account with balance?
        transfer = self.transfers().order_by('last_fail').first()
        if transfer:
            self.logger.info(f'Retrying transfer {transfer}')
            transfer.deploy()
            return transfer
        self.logger.info('Found 0 transfer to retry')

        # any contract to retry?
        contract = self.contracts().order_by('last_fail').first()
        if contract:
            self.logger.info(f'Retrying contract {contract}')
            contract.deploy()
            return contract
        self.logger.info('Found 0 contract to retry')

        # any call to retry?
        call = self.calls().order_by('last_fail').first()
        if call:
            self.logger.info(f'Retrying function {call}')
            call.deploy()
            return call
        self.logger.info('Found 0 call to retry')


def fakehash(leet):
    return f'0x{leet}5EF2D798D17e2ecB37' + str(random.randint(
        1000000000000000, 9999999999999999
    ))


class Success(Provider):
    pass
