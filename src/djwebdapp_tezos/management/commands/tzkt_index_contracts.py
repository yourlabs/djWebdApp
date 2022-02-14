import time
from asgiref.sync import async_to_sync, sync_to_async
from dipdup.datasources.tzkt.datasource import TzktDatasource
from django.core.management.base import BaseCommand
from djwebdapp.models import Account
from djwebdapp_tezos.models import TezosTransaction


class Command(BaseCommand):
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

    help = 'Index contracts transactions using tzkt API and dipdup'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tzkt',
            default='https://api.tzkt.io/',
            type=str,
        )
        parser.add_argument(
            '--tries',
            default=100,
            type=int,
        )

    def handle(self, *args, **options):
        tzkt = options['tzkt']
        tries = options['tries']

        contracts = TezosTransaction.objects.filter(
            blockchain__is_active=True,
            blockchain__provider_class__icontains='tezos',
        ).select_related('blockchain')

        for contract in contracts:
            _tries = tries
            while _tries:
                result = self.sync_contract(contract, tzkt)

                if result:
                    break
                else:
                    _tries -= 1
                    time.sleep(.1)

    @async_to_sync
    async def sync_contract(self, contract, tzkt):
        """
        Index calls for a given contract.
        """

        @sync_to_async
        def handle_result(result):
            contract.call_set.update_or_create(
                hash=result.hash,
                blockchain=contract.blockchain,
                defaults=dict(
                    sender=Account.objects.get_or_create(
                        address=result.sender_address,
                        blockchain=contract.blockchain,
                    )[0],
                    datetime=result.timestamp,
                    level=result.level,
                    args=result.parameter_json,
                    function=result.entrypoint,
                )
            )
            contract.metadata['storage'] = result.storage
            contract.save()

        source = TzktDatasource(tzkt)
        async with source:
            results = await source.get_transactions(
                'target',
                [contract.address],
                0,
                0,
                100000000,
            )
            for result in results:
                await handle_result(result)

            if results:
                return True
