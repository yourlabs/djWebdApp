import logging

from django.db.models import Q

from djwebdapp.models import Address, SmartContract, Call, Transaction
from djwebdapp.provider import Provider
from djwebdapp.signals import call_indexed, contract_indexed

from pytezos import pytezos


class TezosProvider(Provider):
    logger = logging.getLogger('djwebdapp_tezos')

    def index(self):
        client = pytezos.using(shell=self.blockchain.node_set.first().endpoint)

        start_level = current_level = (
            client.shell.head.metadata()['level_info']['level_position']
        )

        reorg = (
            self.blockchain.max_level
            and start_level < self.blockchain.max_level
        )
        if reorg:
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
                            self.index_contract(current_level, op, content)
                        elif content['kind'] == 'transaction':
                            destination = content.get('destination', None)
                            if destination not in addresses:
                                return
                            self.index_call(current_level, op, content)

            current_level -= 1

        # consider head as suceptible to change
        self.blockchain.max_level = start_level - 1

        self.blockchain.save()

    def index_contract(self, level, op, content):
        self.logger.info(f'Syncing origination {op["hash"]}')
        result = content['metadata']['operation_result']
        address = result['originated_contracts'][0]
        contract = SmartContract.objects.get(
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
        self.logger.info(f'Syncing transaction {hash}')
        contract = SmartContract.objects.get(
            blockchain=self.blockchain,
            address=content['destination'],
        )
        call = contract.call_set.filter(
            hash=op['hash'],
        ).select_related('contract').first()
        if not call:
            call = Call(
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
        call_indexed.send(
            sender=type(call),
            instance=call,
        )
        call.state_set('done')
