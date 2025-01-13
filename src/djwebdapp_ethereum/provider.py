import logging

from hexbytes import HexBytes
from web3 import Web3
from web3.exceptions import ContractLogicError

from django.conf import settings

from djwebdapp.models import Account
from djwebdapp_ethereum.models import EthereumEvent, EthereumTransaction
from djwebdapp.provider import Provider


class EthereumProvider(Provider):
    logger = logging.getLogger('djwebdapp_ethereum')
    transaction_class = EthereumTransaction

    def generate_secret_key(self):
        wallet = self.client.eth.account.create()
        return wallet.address, bytes(wallet.key)

    def should_activate_client_middleware(self, endpoint):
        """
        For non-mainnet chains, the client needs to activate an onion
        middleware. See:
        https://web3py.readthedocs.io/en/stable/middleware.html#geth-style-proof-of-authority
        This method checks whether, given the blockchain endpoint, this
        middleware should be activated
        """  # noqa: E501
        middleware_endpoints = [
            'ethlocal',
            'localhost',
            'polygon-mumbai',
        ]
        return len([substr in endpoint for substr in middleware_endpoints])

    def get_client(self, **kwargs):
        endpoint = self.blockchain.node_set.first().endpoint
        client = Web3(Web3.HTTPProvider(endpoint))

        if settings.DEBUG and not self.wallet:  # geth default account
            client.eth.default_account = client.eth.accounts[0]

        if self.should_activate_client_middleware(endpoint):
            from web3.middleware import geth_poa_middleware
            client.middleware_onion.inject(geth_poa_middleware, layer=0)

        return client

    def get_balance(self, address=None):
        weis = self.client.eth.get_balance(
            address
            or getattr(self.wallet, 'address', False)
            or self.client.eth.default_account
        )
        return self.client.from_wei(weis, 'ether')

    @property
    def head(self):
        """
        Return the current block number.
        """
        return self.client.eth.get_block_number()

    def index_level(self, level):
        block = self.client.eth.get_block(level, True)
        for transaction in block.transactions:
            to = transaction.get('to', None)
            if to is None and self.check_hash(transaction['hash'].hex()):
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
        contract.state_set('done')

    def index_call(self, level, transaction):
        self.logger.info(f'EthereumProvider.index_call({transaction})')

        contract = EthereumTransaction.objects.filter(
            blockchain=self.blockchain,
            address=transaction['to'],
        ).first()

        if not contract:
            contract = EthereumTransaction.objects.create(
                blockchain=self.blockchain,
                address=transaction['to'],
                index=False,
            )

        call = contract.call_set.select_subclasses().filter(
            hash=transaction['hash'].hex(),
        ).first()

        tx_receipt = self.client.eth.get_transaction_receipt(
            transaction['hash'].hex(),
        )

        if tx_receipt.status == 0:
            return

        if not call:
            call = EthereumTransaction(
                hash=transaction['hash'].hex(),
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
        if contract.abi:
            interface = self.client.eth.contract(
                address=contract.address,
                abi=contract.abi,
            )

        if self.is_smart_contract_transfer_only(call):
            call.function = 'receive'
            call.amount = self.client.from_wei(call.metadata['value'], 'ether')
        elif contract.abi:
            fn, args = interface.decode_function_input(call.metadata['input'])
            call.function = fn.fn_name
            call.args = args

        call.state_set('done')

    def is_smart_contract_transfer_only(self, call):
        """
        You can send ETH to smart contract without calling a method by implementing
        a `receive` or `fallback` function. In which case, the input value is
        always '0x' (no data sent to the contract).

        This method returns `True` if the transaction is such a call.

        More information here: https://ethereum.stackexchange.com/questions/130936/contract-write-function-has-no-input-data0x
        """  # noqa: E501
        return call.metadata['input'] == '0x'

    def json(self, transaction):
        return {
            key: value.hex() if isinstance(value, HexBytes) else value
            for key, value in transaction.items()
        }

    def send(self, transaction):
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

        args = transaction.get_args()

        for i, inp in enumerate(func.abi.get('inputs', [])):
            if inp['type'] == 'tuple':
                tmp_list_from_tuple = []

                for j, component in enumerate(inp['components']):
                    if component['type'].startswith('bytes32'):
                        tmp_list_from_tuple.append(
                            self.client.to_bytes(hexstr=args[i][j])
                        )
                    else:
                        tmp_list_from_tuple.append(args[i][j])
                args[i] = tuple(tmp_list_from_tuple)

            elif inp['type'].startswith('bytes32'):
                args[i] = self.client.to_bytes(hexstr=args[i])

        tx = func(*args)
        transaction.hash = self.write_transaction(transaction, tx)

    def deploy(self, transaction):
        self.logger.debug(f'{transaction}.deploy(): start')
        transaction.level = self.head

        if transaction.kind == 'contract':
            transaction.sender.last_level = self.head
            self.originate(transaction)
            transaction.sender.save()
        elif transaction.kind == 'function':
            transaction.sender.last_level = self.head
            self.send(transaction)
            transaction.sender.save()
        elif transaction.kind == 'transfer':
            transaction.hash = self.transfer(transaction)
        else:
            transaction.error = f'Unknown transaction kind {transaction.kind}'
            transaction.state_set('failed')
            return

        self.logger.info(f'{transaction}.deploy(): success')

    def transfer(self, transaction):
        tx = {
            'to': transaction.receiver.address,
            'from': transaction.sender.address,
            'value': self.client.to_wei(transaction.amount, 'ether'),
        }
        tx['gas'] = self.client.eth.estimate_gas(tx)
        tx['gasPrice'] = self.client.eth.gas_price
        tx['nonce'] = self.client.eth.get_transaction_count(
            transaction.sender.address
        )
        tx['chainId'] = self.client.eth.chain_id
        signed_txn = self.client.eth.account.sign_transaction(
            tx,
            private_key=transaction.sender.get_secret_key(),
        )
        self.client.eth.send_raw_transaction(signed_txn.rawTransaction)
        return self.client.to_hex(
            self.client.keccak(signed_txn.rawTransaction)
        )

    def originate(self, transaction):
        Contract = self.client.eth.contract(  # noqa
            abi=transaction.abi,
            bytecode=transaction.bytecode,
        )

        tx = Contract.constructor(*transaction.get_args())
        transaction.hash = self.write_transaction(transaction, tx)
        receipt = self.client.eth.wait_for_transaction_receipt(
            transaction.hash)
        transaction.address = receipt.contractAddress

    def write_transaction(self, djwebdapp_transaction, tx):
        sender = djwebdapp_transaction.sender
        nonce = self.client.eth.get_transaction_count(sender.address)
        options = {
            'from': sender.address,
            'nonce': nonce,
        }
        try:
            built = tx.build_transaction(options)
        except ContractLogicError as e:
            djwebdapp_transaction.error = e.message
            raise e
        options['gas'] = self.client.eth.estimate_gas(built)
        signed_txn = self.client.eth.account.sign_transaction(
            built,
            private_key=sender.get_secret_key(),
        )

        self.client.eth.send_raw_transaction(signed_txn.rawTransaction)
        return self.client.to_hex(
            self.client.keccak(signed_txn.rawTransaction)
        )


class EthereumEventProvider(EthereumProvider):
    event_class = EthereumEvent

    def index_init(self):
        super().index_init()
        self.contracts = self.contracts.exclude(
            abi=None,
        )

        self.addresses = self.contracts.values_list(
            'address',
            flat=True,
        )

        head = self.head

        event_filter = {
            'fromBlock': self.blockchain.index_level or 0,
            'toBlock': head,
            'address': self.addresses,
        }

        try:
            logs = self.client.eth.get_logs(event_filter)
        except Exception:
            logs = []
            init_level = self.blockchain.index_level or 0
            number_of_levels_to_increment = self.blockchain.configuration.get(
                'number_of_levels_to_increment',
                50,
            )

            while init_level < head:
                to_block = min(
                    init_level + number_of_levels_to_increment,
                    head,
                )
                event_filter['fromBlock'] = init_level
                event_filter['toBlock'] = to_block
                logs += self.client.eth.get_logs(event_filter)
                init_level = to_block + 1

        self.logs = logs

    def get_min_level(self, items, key):
        return min((item[key] for item in items), default=None)

    def index(self):
        """
        Index EVM blockchains.

        Iterate over each level that included txs and events
        related to indexed contracts.
        """
        self.index_init()

        while len(self.hashes) or len(self.logs):
            index_of_level_in_hashes_tuple = 1
            min_level_hashes = self.get_min_level(
                self.hashes,
                key=index_of_level_in_hashes_tuple,
            )
            min_level_logs = self.get_min_level(
                self.logs,
                key='blockNumber',
            )

            level_to_index = min(
                filter(None, [min_level_hashes, min_level_logs])
            )

            self.logger.info(f'Indexing level {level_to_index}')
            self.index_level(level_to_index)
            self.blockchain.index_level = level_to_index
        self.blockchain.save()

    def index_level(self, level):
        """
        To optimize for compute units on Alchemy/Moralis nodes, we:

        #. Filter logs fetched for a range of level at init to restrict them
           to the current level

        #. only query the full block to index relevant transactions if:

           #. a log is included at the current level in which case we index
              both the log and the parent transaction. Since the log could
              have been emitted from a transaction that was not originated
              from an indexed contract, we still index that transaction to
              be able to retrieve it later on.
           #. a transaction that was spooled is awaiting indexing to ensure
              it was included on-chain (contract origination,
              spooled contract call, etc).

        As such, no node requests should be made if there are no spooled
        transactions awaiting confirmation nor any events were emitted
        at the current level.
        """
        logs_at_level = list(filter(
            lambda log: log["blockNumber"] == level,
            self.logs,
        ))
        logs_tx_hash = [log["transactionHash"].hex() for log in logs_at_level]

        hashes_at_level = list(filter(
            lambda hash_tuple: hash_tuple[1] == level,
            self.hashes,
        ))
        hashes = [hash_tuple[0] for hash_tuple in hashes_at_level]

        if len(hashes):
            block = self.client.eth.get_block(level, True)
            for transaction in block.transactions:
                to = transaction.get('to', None)
                if to is None and transaction['hash'].hex() in hashes:
                    self.index_contract(level, transaction)
                elif (
                    to in self.addresses
                    or (transaction['hash'].hex() in logs_tx_hash and to)
                ):
                    self.index_call(level, transaction)

        for log in logs_at_level:
            if not log["removed"]:
                self.index_log(log)

        self.hashes = list(filter(
            lambda hash_tuple: hash_tuple[1] > level,
            self.hashes,
        ))

        self.logs = list(filter(
            lambda log: log['blockNumber'] != level,
            self.logs
        ))

    def get_contract_event_names(self, contract_abi):
        events = []
        for entry in contract_abi:
            if (
                "type" in entry
                and entry["type"] == "event"
                and "name" in entry
            ):
                events.append(entry["name"])
        return events

    def index_log(self, log):
        # In case of it's a log for the contract creation, right now it
        # will not be indexed by 'index_call' or 'index_contract' methods
        # so the transaction is not created
        # So right now I return if the tx not exists

        transaction, created = self.transaction_class.objects.update_or_create(
            blockchain=self.blockchain,
            hash=log["transactionHash"].hex(),
            defaults=dict(
                level=log["blockNumber"],
            )
        )
        transaction.state_set("done")

        is_contract_deployment_tx = 'to' not in log

        if created and is_contract_deployment_tx:
            transaction.index = False
            transaction.save()

        contract = self.transaction_class.objects.filter(
            address=log["address"]
        ).first()
        contract_ci = self.client.eth.contract(
            address=contract.address,
            abi=contract.abi,
        )
        event_names = self.get_contract_event_names(contract_ci.abi)
        for event_name in event_names:
            event = getattr(contract_ci.events, event_name)
            event_data = event().process_receipt({"logs": [log]})
            if event_data:
                self.event_class.objects.update_or_create(
                    name=event_name,
                    contract=contract,
                    transaction=transaction,
                    args=event_data[0]["args"],
                    event_index=event_data[0]["logIndex"],
                )
