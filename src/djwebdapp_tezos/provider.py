import asyncio
import logging
import time
from mnemonic import Mnemonic

from asgiref.sync import async_to_sync, sync_to_async

from dipdup.datasources.tzkt.datasource import TzktDatasource

from django.core.exceptions import ValidationError

from djwebdapp.models import Address, SmartContract, Transfer, Call
from djwebdapp.exceptions import PermanentError
from djwebdapp.provider import Provider

from pytezos import pytezos, Key
from pytezos.rpc.node import RpcError


logger = logging.getLogger('djtezos.tezos')


class TezosProvider(Provider):
    """
    djWebdApp provider for the Tezos blockchain.

    It takes a ``tzkt`` configuration key to specify the URL of the tzkt API to
    use, ie.:

    .. code-block:: python

        blockchain = Blockchain.objects.create(
            name='Tezos Mainnet',
            provider_class='djwebdapp_tezos.provider.TezosProvider',
            configuration=dict(
                tzkt='https://api.tzkt.io/',
            ),
        )
    """

    @async_to_sync
    async def sync_contract(self, contract):
        """
        Index calls for a given contract.
        """

        @sync_to_async
        def handle_origination(origination):
            contract_row = SmartContract.objects.filter(address=None, hash=origination.hash).first()
            if contract_row:
                contract_row.address = origination.originated_contract_address
                contract_row.save()

        @sync_to_async
        def handle_result(result):
            contract.call_set.update_or_create(
                hash=result.hash,
                blockchain=contract.blockchain,
                defaults=dict(
                    sender=Address.objects.get_or_create(
                        address=result.sender_address,
                        blockchain=contract.blockchain,
                    )[0],
                    datetime=result.timestamp,
                    level=result.level,
                    storage=result.storage,
                    args=result.parameter_json,
                    function=result.entrypoint,
                )
            )

        @sync_to_async
        def get_sender():
            return contract.sender

        source = TzktDatasource(
            contract.blockchain.configuration['tzkt']
        )
        sender = await get_sender()
        async with source:
            originated_addresses = await source.get_originated_contracts(sender.address)
            originations = await source.get_originations(
                set(originated_addresses),
                0,
                0,
                100000000,
            )
            for origination in originations:
                await handle_origination(origination)

            if contract.address:
                results = await source.get_transactions(
                    'target',
                    [contract.address],
                    0,
                    0,
                    100000000,
                )
                for result in results:
                    await handle_result(result)

    def reveal(self, private_key, sender=None):
        client = pytezos.using(
            key=Key.from_secret_exponent(private_key),
            shell=self.blockchain.endpoint,
        )
        # key reveal dance
        try:
            operation = client.reveal().autofill().sign().inject()
        except RpcError as e:
            if 'id' in e.args[0] and 'previously_revealed_key' in e.args[0]['id']:
                return client
            raise e
        else:
            logger.debug(f'Revealing {sender}')
            opg = self.wait_injection(client, operation)
            if not opg:
                raise ValidationError(f'Could not reveal {sender}')

    def get_client(self, private_key, reveal=False, sender=None):
        client = pytezos.using(
            key=Key.from_secret_exponent(private_key),
            shell=self.blockchain.endpoint,
        )
        if reveal:
            self.reveal(private_key, sender)

        return client

    def wait_injection(self, client, operation):
        opg = None
        tries = 100
        while tries and not opg:
            try:
                opg = client.shell.blocks[-20:].find_operation(operation['hash'])
                if opg['contents'][0]['metadata']['operation_result']['status'] == 'applied':
                    logger.info(f'Revealed {client.key.public_key_hash()}')
                    break
                else:
                    raise StopIteration()
            except StopIteration:
                opg = None
            tries -= 1
            time.sleep(100 - tries)
        return opg

    def deploy(self, transaction):
        if isinstance(transaction, Transfer):
            return self.transfer(transaction)
        elif isinstance(transaction, Call):
            return self.send(transaction)
        elif isinstance(transaction, SmartContract):
            return self.originate(transaction)
        else:
            return PermanentError("Action does not exist")

    def transfer(self, transaction):
        """
        rpc error if balance too low :
        RpcError ({'amount': '120000000000000000',
              'balance': '3998464237867',
              'contract': 'tz1gjaF81ZRRvdzjobyfVNsAeSC6PScjfQwN',
              'id': 'proto.006-PsCARTHA.contract.balance_too_low',
              'kind': 'temporary'},)
        """
        logger.debug(f'Transfering {transaction.amount} from {transaction.sender} to {transaction.receiver}')
        client = self.get_client(
            transaction.sender.private_key,
            reveal=True,
            sender=transaction.sender.address
        )
        tx = client.transaction(
            destination=transaction.receiver.address,
            amount=transaction.amount,
        ).autofill().sign()
        result = self.write_transaction(tx, transaction)
        return result


    def originate(self, transaction):
        transaction.storage = transaction.get_storage()
        logger.debug(f'{transaction}.originate({transaction.storage}): start')
        client = self.get_client(
            transaction.sender.private_key,
            reveal=True,
            sender=transaction.sender.address
        )

        if not client.balance():
            raise ValidationError(
                f'{transaction.sender.address} needs more than 0 tezies')

        tx = client.origination(dict(
            code=transaction.contract_micheline,
            storage=transaction.storage,
        )).autofill().sign()

        result = self.write_transaction(tx, transaction)

        logger.info(f'{transaction.name}.deploy({transaction.storage}): {result}')
        return result

    def write_transaction(self, tx, transaction):
        origination = tx.inject(
            _async=True,
            # this seems not to be working for us, systematic TimeoutError
            #min_confirmations=transaction.blockchain.confirmation_blocks,
        )
        transaction.gas = origination['contents'][0]['fee']
        transaction.hash = origination['hash']

    def send(self, transaction):
        logger.debug(f'{transaction}({transaction.args}): get_client')
        client = self.get_client(transaction.sender.private_key)
        logger.debug(f'{transaction}({transaction.args}): counter = {client.account()["counter"]}')
        ci = client.contract(transaction.contract_address)
        method = getattr(ci, transaction.function)

        client = self.reveal(
            transaction.sender.private_key,
            sender=transaction.sender.address
        )
        try:
            tx = method(*transaction.args)
        except ValueError as e:
            raise PermanentError(*e.args)
        result = self.write_transaction(tx, transaction)
        logger.debug(f'{transaction}({transaction.args}): {result}')
        return result

    def create_wallet(self, passphrase):
        mnemonic = Mnemonic('english').generate(128)
        key = Key.from_mnemonic(mnemonic, passphrase, curve=b'ed')
        return key.public_key_hash(), key.secret_exponent
