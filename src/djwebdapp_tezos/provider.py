import logging

from django.db.models import Q

from djwebdapp.models import Address
from djwebdapp.provider import Provider
from djwebdapp.signals import call_indexed, contract_indexed

from djwebdapp_tezos.models import TezosTransaction

from pytezos import pytezos


class TezosProvider(Provider):
    logger = logging.getLogger('djwebdapp_tezos')
    transaction_class = TezosTransaction

    def get_client(self, wallet=None):
        return pytezos.using(shell=self.blockchain.node_set.first().endpoint)

    @property
    def head(self):
        return self.client.shell.head.metadata(
            )['level_info']['level_position']

    def index_level(self, level):
        block = self.client.shell.blocks[level]
        for ops in block.operations():
            for op in ops:
                hash = op['hash']
                for content in op.get('contents', []):
                    if content['kind'] == 'origination':
                        if 'metadata' not in content:
                            continue
                        result = content['metadata']['operation_result']
                        address = result['originated_contracts'][0]
                        if (
                            address not in self.addresses
                            and hash not in self.hashes
                        ):
                            # skip unknown contract originations
                            continue
                        self.index_contract(level, op, content)
                    elif content['kind'] == 'transaction':
                        destination = content.get('destination', None)
                        if destination not in self.addresses:
                            continue
                        self.index_call(level, op, content)

    def index_contract(self, level, op, content):
        self.logger.info(f'Syncing origination {op["hash"]}')
        result = content['metadata']['operation_result']
        address = result['originated_contracts'][0]
        contract = self.transaction_class.objects.get(
            Q(address=address) | Q(hash=op['hash'])
        )
        contract.level = level
        contract.address = address
        contract.hash = hash
        contract.gas = content['fee']
        contract.metadata = content
        contract_indexed.send(
            sender=type(contract),
            instance=contract,
        )
        contract.state_set('done')

    def index_call(self, level, op, content):
        self.logger.info(f'Syncing transaction {op["hash"]}')
        contract = self.transaction_class.objects.get(
            blockchain=self.blockchain,
            address=content['destination'],
        )
        call = contract.call_set.filter(
            hash=op['hash'],
        ).first()
        if not call:
            call = self.transaction_class(
                hash=op['hash'],
                contract=contract,
                blockchain=self.blockchain,
            )

        call.metadata = content
        call.gas = content['fee']
        call.level = level
        call.sender, _ = Address.objects.get_or_create(
            address=content['source'],
            blockchain=self.blockchain,
        )
        call.function = call.metadata['parameters']['entrypoint']
        method = getattr(contract.interface, call.function)
        args = method.decode(call.metadata['parameters']['value'])
        call.args = args[call.function]
        call_indexed.send(
            sender=type(call),
            instance=call,
        )
        call.state_set('done')
