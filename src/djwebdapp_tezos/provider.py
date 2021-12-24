import asyncio
from asgiref.sync import async_to_sync, sync_to_async


from dipdup.datasources.tzkt.datasource import TzktDatasource

from djwebdapp.models import Address
from djwebdapp.provider import Provider


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

        source = TzktDatasource(
            contract.blockchain.configuration['tzkt']
        )
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
