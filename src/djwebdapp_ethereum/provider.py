import logging

from hexbytes import HexBytes
from web3 import Web3

from djwebdapp.models import Address
from djwebdapp_ethereum.models import EthereumTransaction
from djwebdapp.provider import Provider
from djwebdapp.signals import call_indexed, contract_indexed


class EthereumProvider(Provider):
    logger = logging.getLogger('djwebdapp_ethereum')
    transaction_class = EthereumTransaction

    def get_client(self, wallet=None):
        client = Web3(Web3.HTTPProvider('http://ethlocal:8545'))
        client.eth.default_account = client.eth.accounts[0]
        from web3.middleware import geth_poa_middleware
        client.middleware_onion.inject(geth_poa_middleware, layer=0)
        return client

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
        call = contract.call_set.filter(
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
        call.sender, _ = Address.objects.get_or_create(
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
