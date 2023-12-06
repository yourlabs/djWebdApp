from decimal import Decimal
import logging
import requests
import urllib

from django.db.models import Q, signals
from django.core.exceptions import ValidationError
from pytezos.operation.result import OperationResult
from pytezos.rpc import RpcError

from djwebdapp.exceptions import PermanentError
from djwebdapp.models import Account, account_setup
from djwebdapp.provider import Provider

from djwebdapp_tezos.models import TezosTransaction

from pytezos import pytezos, Key


class TezosProvider(Provider):
    logger = logging.getLogger('djwebdapp_tezos')
    transaction_class = TezosTransaction

    def generate_secret_key(self):
        key = Key.generate(export=False)
        return key.public_key_hash(), key.secret_exponent

    def get_client(self, **kwargs):
        if self.wallet:
            kwargs['key'] = Key.from_secret_exponent(
                self.wallet.get_secret_key()
            )
        return pytezos.using(
            shell=self.blockchain.node_set.first().endpoint,
            **kwargs,
        )

    @property
    def head(self):
        return self.client.shell.head.metadata()['level_info']['level']

    def get_address(self):
        return self.client.key.public_key_hash()

    def get_balance(self, address=None):
        return Decimal(
            self.client.account(address or self.get_address())['balance']
        )

    def index_level(self, level):
        block = self.client.shell.blocks[level]
        for ops in block.operations():
            for number, op in enumerate(ops):
                for content in op.get('contents', []):
                    self.index_content(level, number, op, content)

    def index_content(self, level, number, op, content):
        self.logger.info(f'Indexing content {number}@{level} {op["hash"]}')
        # index content normally
        hash = op['hash']
        if (
            content['kind'] == 'origination'
            and 'metadata' in content
        ):
            result = content['metadata']['operation_result']
            address = result['originated_contracts'][0]
            if (
                address not in self.addresses
                and not self.check_hash(hash)
            ):
                # skip unknown contract originations
                return
            self.index_contract(level, op, content, number=number)
        elif (
            content['kind'] == 'transaction'
            and (
                content.get('destination', None) in self.addresses
                or self.check_hash(hash)
            )
        ):
            self.index_call(level, op, content, number=number)
        else:
            # index internal transactions if necessary
            for internal_op in OperationResult.iter_contents(content):
                if (
                    internal_op.get('destination', '') in self.addresses
                    or internal_op.get('source', '') in self.addresses
                ):
                    self.index_call(
                        level,
                        op,
                        content,
                        number=number,
                    )
                    break

    def index_contract(self, level, op, content, number):
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
        contract.number = number
        contract.sender, _ = self.blockchain.account_set.get_or_create(
            address=op['contents'][0]['source'],
            blockchain=self.blockchain,
        )
        contract.state_set('done')

    def is_implicit_contract(self, address):
        return len(address) == 36 and address[:2] == 'tz'

    def index_origination(self, level, hash, content, caller=None,
                          number=None):
        self.logger.info(f'Syncing origination {hash}')

        originated_contracts = []
        for originated_address in content['result']['originated_contracts']:
            contract, created = self.transaction_class.objects.get_or_create(
                address=originated_address,
                blockchain=self.blockchain,
                caller=caller,
            )
            contract.level = level
            contract.hash = hash
            contract.gas = content.get('fee', 0)
            contract.metadata = content
            contract.nonce = content.get('nonce', -1)
            contract.sender = self.get_account(content['source'])
            contract.number = number
            contract.state_set('done')
            originated_contracts.append(contract)

        return originated_contracts

    def get_account(self, address):
        sender = Account.objects.filter(
            address=address,
            blockchain=self.blockchain,
        ).first()

        if not sender:
            sender = Account.objects.create(
                address=address,
                blockchain=self.blockchain,
                index=False,
            )

        return sender

    def index_transaction(self, level, hash, content, caller=None,
                          number=None):
        self.logger.info(f'Syncing transaction {hash}')

        counter = caller.counter if caller else content.get('counter', None)

        # figure destination contract
        destination_address = content['destination']

        if self.is_implicit_contract(destination_address):
            # this transaction targets an account
            contract = None
            receiver, _ = Account.objects.get_or_create(
                blockchain=self.blockchain,
                address=destination_address,
            )
            qs = receiver.transaction_received
        else:
            # this transaction targets a contract
            receiver = None
            contract = self.transaction_class.objects.filter(
                blockchain=self.blockchain,
                address=destination_address,
            ).first()
            if not contract:
                contract = self.transaction_class.objects.create(
                    blockchain=self.blockchain,
                    address=destination_address,
                    index=False,
                    number=number,
                )
            qs = contract.call_set.select_subclasses()

        call = qs.filter(
            hash=hash,
            nonce=content.get('nonce', -1),
            counter=counter,
            # we shouldn't take the level into account
            # when filtering due to confirm transactions
            # that "overide" the level in djwebdapp.provider.index
            # level=level,  <-- don't uncomment this
        ).first()

        if not call:
            call = self.transaction_class(
                hash=hash,
                counter=counter,
                contract=contract,
                receiver=receiver,
                blockchain=self.blockchain,
                nonce=content.get('nonce', -1),
                amount=int(content.get('amount', 0)),
                state='held',
                caller=caller,
                number=number,
                level=level,
            )

        # update call
        call.metadata = content
        call.sender = self.get_account(content['source'])

        # patch against empty args in pytezes
        if 'parameters' in content:
            call.function = content['parameters']['entrypoint']
            method = getattr(contract.interface, call.function)
            args = method.decode(call.metadata['parameters']['value'])
            if args == call.function:
                call.args = []
            else:
                if call.function not in args:
                    call.args = args
                else:
                    call.args = args[call.function]

        # save and return call
        call.state_set('done')

        return call

    def index_call(self, level, op, content, number=None):
        self.logger.info(f'Syncing transaction {op["hash"]}')

        operations = [op for op in OperationResult.iter_contents(content)]
        internal_operations = operations[1:]

        source = self.index_transaction(
            level,
            op['hash'],
            content,
            number=number,
        )

        internal_transactions = []
        for operation_content in internal_operations:
            if operation_content['kind'] == 'transaction':
                if 'destination' in operation_content:
                    internal_transaction = self.index_transaction(
                        level,
                        op['hash'],
                        operation_content,
                        source,
                        number=number,
                    )
                    internal_transactions.append(internal_transaction)

            if operation_content['kind'] == 'origination':
                if 'originated_contracts' in operation_content['result']:
                    internal_originations = self.index_origination(
                        level,
                        op['hash'],
                        operation_content,
                        source,
                        number=number,
                    )
                    internal_transactions += internal_originations

        return source

    def transfer(self, transaction):
        """ Execute a transfer transaction. """

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
        if not self.client.balance():
            raise ValidationError(
                f'{transaction.sender.address} needs more than 0 tezies')
        elif not self.wallet.revealed:
            try:
                self.client.reveal().send(min_confirmations=1)
            except RpcError as exc:
                if len(exc.args) > 1:
                    raise

                if not exc.args[0]['id'].endswith('previously_revealed_key'):
                    raise
            self.wallet.revealed = True
            self.wallet.save()

        self.logger.debug(f'{transaction}.deploy(): start')
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
        self.logger.info(f'{transaction}.deploy(): success')

    def originate(self, transaction):
        tx = self.client.origination(dict(
            code=transaction.micheline,
            storage=transaction.get_args(),
        )).autofill().sign()

        self.write_transaction(tx, transaction)

    def write_transaction(self, tx, transaction):
        origination = tx.inject(
            _async=False,
        )
        transaction.level = self.head + 1  # it'll be in the next block
        transaction.gas = origination['contents'][0]['fee']
        transaction.hash = origination['hash']
        transaction.counter = origination['contents'][0]['counter']
        transaction.save()

    def send(self, transaction):
        self.logger.debug(
            f'{transaction}: counter = {self.client.account()["counter"]}'
        )
        ci = self.client.contract(transaction.contract.address)
        method = getattr(ci, transaction.function)
        try:
            args = transaction.get_args()
            if isinstance(args, dict):
                tx = method(**args)
            else:
                tx = method(*args)
            if transaction.amount:
                tx = tx.with_amount(transaction.amount)
        except ValueError as e:
            raise PermanentError(*e.args)
        self.write_transaction(tx, transaction)

    def download(self, target):
        """
        Import transactions from tzkt for a contract
        """
        api = self.blockchain.configuration.get(
            'tzkt_url',
            'https://api.tzkt.io',  # default indexer?
        )
        url = f'{api}/v1/operations/transactions?'
        url += f'&target={urllib.parse.quote(target)}'
        url += f'&level.le={self.head - 1}'

        contract, _ = self.transaction_class.objects.get_or_create(
            blockchain=self.blockchain,
            address=target,
        )

        def get(offset, limit):
            return requests.get(url + f'&offset={offset}&limit={limit}').json()

        def yield_operations():
            offset = 0
            limit = 10_000
            while data := get(offset, limit):
                for operation in data:
                    if operation['type'] != 'transaction':
                        continue

                    if operation['status'] != 'applied':
                        continue

                    yield operation
                offset += limit

        total = 0
        operations = dict()
        for operation in yield_operations():
            total += 1

            # generate a key for the operation group
            key = (
                operation['level'],
                operation['hash'],
                operation['counter'],
                operation.get('nonce', 0),
            )

            operations[key] = operation

        # disable automatic refresh of balances to speed up the whole process
        signals.pre_save.disconnect(account_setup, sender=Account)
        # we're also going to cache Account objects
        accounts = dict()

        # fetch all calls we already have in DB
        calls = {
            (call.level, call.hash, call.counter, call.nonce): call
            for call in self.transaction_class.objects.filter(
                contract=contract,
                state__in=('confirm', 'done'),
            )
        }

        number = 0
        for key in sorted(operations.keys()):
            number += 1
            level, hash, counter, nonce = key
            self.logger.debug(' '.join((
                f'[{number}/{total}]',
                hash,
                f'level={level}',
                f'counter={counter}',
                f'nonce={nonce if isinstance(nonce, int) else -1}',
            )))

            if key in calls:
                continue  # let's not update for now

            operation = operations[key]

            if operation['sender']['address'] in accounts:
                sender = accounts[operation['sender']['address']]
            else:
                sender, _ = Account.objects.get_or_create(
                    address=operation['sender']['address'],
                    blockchain=self.blockchain,
                )
                accounts[sender.address] = sender

            function = operation['parameter']['entrypoint']
            args = operation['parameter']['value']

            for key, value in args.items():
                try:
                    args[key] = int(value)
                except ValueError:
                    continue

            call = self.transaction_class(
                blockchain=self.blockchain,
                contract=contract,
                sender=sender,
                level=level,
                hash=hash,
                counter=counter,
                nonce=nonce if isinstance(nonce, int) else -1,
                kind='call',
                function=function,
                args=args,
                metadata=operation,
                gas=operation['gasUsed'],
            )
            call.state_set('done')

        # reconnect Account signal
        signals.pre_save.connect(account_setup, sender=Account)
