import logging
from mnemonic import Mnemonic

from asgiref.sync import async_to_sync, sync_to_async

from dipdup.datasources.tzkt.datasource import TzktDatasource

from django.core.exceptions import ValidationError
from django.db.models import Q

from djwebdapp.models import Address, SmartContract, Transfer, Call, Transaction
from djwebdapp.exceptions import PermanentError
from djwebdapp.provider import Provider
from djwebdapp.signals import call_indexed, contract_indexed

from pytezos import pytezos, Key
from pytezos.rpc.node import RpcError




class TezosProvider(Provider):
    logger = logging.getLogger('djwebdapp_tezos')

    def index(self):
        client = pytezos.using(shell=self.blockchain.node_set.first().endpoint)

        start_level = current_level = client.shell.head.metadata()['level_info']['level_position']
        if self.blockchain.max_level and start_level < self.blockchain.max_level:
            # reorg
            Transaction.objects.filter(
                sender__blockchain=self.blockchain,
                level__gte=self.blockchain.max_level,
            ).exclude(level=None).update(
                level=None,
                hash=None,
                address=None,
                state='deleted',
            )
            self.blockchain.max_level = self.blockchain.max_level
            self.blockchain.save()
            return  # commit to reorg in a transaction
        if self.blockchain.max_level and start_level == self.blockchain.max_level:
            # no need to go all way back further if we are up to date just
            # check the head
            max_depth = 1
        if self.blockchain.max_level and start_level > self.blockchain.max_level:
            # go all way back to where we left
            max_depth = (start_level - self.blockchain.max_level) or 1
        if not self.blockchain.max_level:
            # go with an arbitrary backlog
            max_depth = 500
        hashes = Transaction.objects.filter(
            blockchain=self.blockchain
        ).exclude(
            hash=None
        ).values_list('hash', flat=True)
        contracts = SmartContract.objects.exclude(
            address=None,
        ).filter(
            blockchain=self.blockchain,
        )
        addresses = contracts.values_list(
            'address',
            flat=True,
        )
        while current_level and start_level - current_level < max_depth:
            print('level', current_level)
            block = client.shell.blocks[current_level]
            for ops in block.operations():
                for op in ops:
                    hash = op['hash']
                    for content in op.get('contents', []):
                        if content['kind'] == 'origination':
                            if 'metadata' not in content:
                                continue
                            result = content['metadata']['operation_result']
                            address = result['originated_contracts'][0]
                            if address not in addresses and hash not in hashes:
                                # skip unknown contract originations
                                continue

                            contract = SmartContract.objects.get(
                                Q(address=address) | Q(hash=hash)
                            )

                            self.logger.info(f'Syncing origination from {hash}')
                            contract.level = current_level
                            contract.address = address
                            contract.hash = hash
                            contract.gas = content['fee']
                            contract.metadata = content
                            contract_indexed.send(
                                sender=type(contract),
                                instance=contract,
                            )
                            contract.state_set('done')
                        elif content['kind'] == 'transaction':
                            self.logger.info(f'Syncing transaction from {hash}')
                            destination = content.get('destination', None)
                            if destination in addresses:
                                self.index_call(current_level, op, content, contracts, self.blockchain)

            current_level -= 1
        self.blockchain.max_level = start_level - 1  # consider head as suceptible to change
        self.blockchain.save()

    def index_call(self, level, op, content, contracts, blockchain):
        contract = contracts.get(address=content['destination'])
        parameters = content.get('parameters', {})
        call = contract.call_set.filter(
            hash=op['hash'],
        ).select_related('contract').first()
        if not call:
            call = Call(
                hash=op['hash'],
                contract=contract,
                blockchain=self.blockchain,
            )
        call.state = 'done'
        call.metadata = content
        call.gas = content['fee']
        call.level = level
        call.sender, _ = Address.objects.get_or_create(
            address=content['source'],
            blockchain=self.blockchain,
        )
        call_indexed.send(
            sender=type(call),
            instance=call,
        )
        call.save()
