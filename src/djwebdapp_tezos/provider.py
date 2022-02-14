from decimal import Decimal
import logging

from django.db.models import Q
from django.core.exceptions import ValidationError

from djwebdapp.exceptions import PermanentError
from djwebdapp.models import Account
from djwebdapp.provider import Provider

from djwebdapp_tezos.models import TezosTransaction

from pytezos import pytezos, Key


class TezosProvider(Provider):
    logger = logging.getLogger('djwebdapp_tezos')
    transaction_class = TezosTransaction

    def generate_secret_key(self):
        key = Key.generate()
        return key.public_key_hash(), key.secret_exponent

    def get_client(self, **kwargs):
        if self.wallet:
            kwargs['key'] = Key.from_secret_exponent(self.wallet.secret_key)
        return pytezos.using(
            shell=self.blockchain.node_set.first().endpoint,
            **kwargs,
        )

    @property
    def head(self):
        return self.client.shell.head.metadata(
            )['level_info']['level']

    def get_address(self):
        return self.client.key.public_key_hash()

    def get_balance(self, address=None):
        return Decimal(
            self.client.account(address or self.get_address())['balance']
        )

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
        contract.hash = op['hash']
        contract.gas = content['fee']
        contract.metadata = content
        contract.sender, _ = self.blockchain.account_set.get_or_create(
            address=op['contents'][0]['source'],
            blockchain=self.blockchain,
        )
        contract.state_set('done')

    def index_call(self, level, op, content):
        self.logger.info(f'Syncing transaction {op["hash"]}')
        contract = self.transaction_class.objects.get(
            blockchain=self.blockchain,
            address=content['destination'],
        )
        call = contract.call_set.select_subclasses().filter(
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
        call.sender, _ = Account.objects.get_or_create(
            address=content['source'],
            blockchain=self.blockchain,
        )
        call.function = call.metadata['parameters']['entrypoint']
        method = getattr(contract.interface, call.function)
        args = method.decode(call.metadata['parameters']['value'])
        call.args = args[call.function]
        call.state_set('done')

    def transfer(self, transaction):
        """
        rpc error if balance too low :
        RpcError ({'amount': '120000000000000000',
              'balance': '3998464237867',
              'contract': 'tz1gjaF81ZRRvdzjobyfVNsAeSC6PScjfQwN',
              'id': 'proto.006-PsCARTHA.contract.balance_too_low',
              'kind': 'temporary'},)
        """
        tx = self.client.transaction(
            destination=transaction.receiver.address,
            amount=transaction.amount,
        ).autofill().sign()
        result = self.write_transaction(tx, transaction)
        return result

    def deploy(self, transaction):
        if transaction.kind == 'contract':
            self.originate(transaction)
        elif transaction.kind == 'function':
            self.send(transaction)
        elif transaction.kind == 'transfer':
            self.transfer(transaction)
        else:
            transaction.error = f'Unknown transaction kind {transaction.kind}'
            transaction.state_set('failed')
            return

        transaction.sender.last_level = self.head
        transaction.sender.save()

    def originate(self, transaction):
        self.logger.debug(
            f'{transaction}.originate({transaction.args}): start')

        if not self.client.balance():
            raise ValidationError(
                f'{transaction.sender.address} needs more than 0 tezies')

        tx = self.client.origination(dict(
            code=transaction.micheline,
            storage=transaction.args,
        )).autofill().sign()

        self.write_transaction(tx, transaction)

        self.logger.info(
            f'{transaction}.deploy({transaction.args}): success!')

    def write_transaction(self, tx, transaction):
        transaction.level = self.head
        origination = tx.inject(
            _async=False,
        )
        transaction.gas = origination['contents'][0]['fee']
        transaction.hash = origination['hash']
        transaction.save()

    def send(self, transaction):
        self.logger.debug(
            f'{transaction}: counter = {self.client.account()["counter"]}'
        )
        ci = self.client.contract(transaction.contract.address)
        method = getattr(ci, transaction.function)
        try:
            tx = method(*transaction.args)
        except ValueError as e:
            raise PermanentError(*e.args)
        result = self.write_transaction(tx, transaction)
        self.logger.debug(f'{transaction}({transaction.args}): {result}')
        return result
