import logging

from hexbytes import HexBytes
from web3 import Web3

from django.conf import settings

from djwebdapp.models import Account
from djwebdapp_ethereum.models import EthereumTransaction
from djwebdapp.provider import Provider
from djwebdapp.signals import call_indexed, contract_indexed


class EthereumProvider(Provider):
    logger = logging.getLogger('djwebdapp_ethereum')
    transaction_class = EthereumTransaction

    def generate_secret_key(self):
        wallet = self.client.eth.account.create()
        return wallet.address, bytes(wallet.privateKey)

    def get_client(self, **kwargs):
        endpoint = self.blockchain.node_set.first().endpoint
        client = Web3(Web3.HTTPProvider(endpoint))

        if settings.DEBUG and not self.wallet:  # geth default account
            client.eth.default_account = client.eth.accounts[0]

        if 'ethlocal' in endpoint or 'localhost' in endpoint:
            from web3.middleware import geth_poa_middleware
            client.middleware_onion.inject(geth_poa_middleware, layer=0)
        return client

    def get_balance(self, address=None):
        weis = self.client.eth.getBalance(
            address
            or self.client.eth.default_account
        )
        return self.client.fromWei(weis, 'ether')

    def transfer(self, receiver, amount, min_confirmations=None):
        self.client.eth.send_raw_transaction(dict(
            to=receiver,
            value=self.client.toWei(amount, 'ether'),
        ))

    @property
    def head(self):
        return self.client.eth.block_number

    def index_level(self, level):
        block = self.client.eth.get_block(level)
        for hash in block.transactions:
            transaction = self.client.eth.get_transaction(hash)
            to = transaction.get('to', None)
            if to is None and transaction['hash'].hex() in self.hashes:
                self.index_contract(level, transaction)
            elif to in self.addresses:
                self.index_call(level, transaction)

    def index_contract(self, level, transaction):
        self.logger.info(f'Syncing origination {transaction["hash"]}')
        contract = EthereumTransaction.objects.get(
            blockchain=self.blockchain,
            hash=transaction['hash'].hex(),
        )
        contract.level = level
        contract.gas = transaction['gas']
        contract.metadata = self.json(transaction)
        contract_indexed.send(
            sender=self.transaction_class,
            instance=contract,
        )
        contract.state_set('done')

    def index_call(self, level, transaction):
        self.logger.info(f'EthereumProvider.index_call({transaction})')
        contract = EthereumTransaction.objects.get(
            blockchain=self.blockchain,
            address=transaction['to'],
        )
        call = contract.call_set.select_subclasses().filter(
            hash=transaction['hash'],
        ).first()
        if not call:
            call = EthereumTransaction(
                hash=transaction['hash'],
                contract=contract,
                blockchain=self.blockchain,
            )
        call.metadata = self.json(transaction)
        call.gas = transaction['gas']
        call.level = level
        call.sender, _ = Account.objects.get_or_create(
            address=transaction['from'],
            blockchain=self.blockchain,
        )
        interface = self.client.eth.contract(
            address=contract.address,
            abi=contract.abi,
        )
        fn, args = interface.decode_function_input(call.metadata['input'])
        call.function = fn.fn_name
        call.args = args
        call_indexed.send(
            sender=self.transaction_class,
            instance=call,
        )
        call.state_set('done')

    def json(self, transaction):
        return {
            key: str(value) if isinstance(value, HexBytes) else value
            for key, value in transaction.items()
        }

    def send(self, transaction):
        self.logger.debug(f'{transaction} deploy: start')

        Contract = self.client.eth.contract(  # noqa
            abi=transaction.contract.abi,
            address=transaction.contract.address,
        )
        funcs = Contract.find_functions_by_name(transaction.function)
        if not funcs:
            raise Exception(
                f'{transaction.function} not found in {transaction.contract}'
            )

        func = funcs[0]

        args = list(transaction.args)

        for i, inp in enumerate(func.abi.get('inputs', [])):
            if inp['type'].startswith('bytes32'):
                args[i] = self.client.toBytes(hexstr=args[i])

        tx = func(*args)

        result = self.write_transaction(transaction.sender, tx)

        self.logger.info(f'{transaction}: success')
        return result

    def deploy(self, transaction):
        transaction.sender.last_level = self.head

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

        transaction.sender.save()

    def originate(self, transaction):
        self.logger.debug(f'{transaction}.deploy({transaction.args}): start')

        Contract = self.client.eth.contract(  # noqa
            abi=transaction.abi,
            bytecode=transaction.bytecode,
        )

        tx = Contract.constructor(*transaction.args)
        transaction.hash = self.write_transaction(
            transaction.sender,
            tx,
        )
        receipt = self.client.eth.wait_for_transaction_receipt(
            transaction.hash)
        transaction.address = receipt.contractAddress
        transaction.save()
        self.logger.info(f'{transaction}.deploy({transaction.args}): success')

    def write_transaction(self, sender, tx):
        nonce = self.client.eth.getTransactionCount(sender.address)
        options = {
            'from': sender.address,
            'nonce': nonce,
        }
        options['gas'] = self.client.eth.estimateGas(
            tx.buildTransaction(options)
        )
        built = tx.buildTransaction(options)
        signed_txn = self.client.eth.account.sign_transaction(
            built,
            private_key=sender.secret_key,
        )

        self.client.eth.sendRawTransaction(signed_txn.rawTransaction)
        return self.client.toHex(
            self.client.keccak(signed_txn.rawTransaction)
        )
