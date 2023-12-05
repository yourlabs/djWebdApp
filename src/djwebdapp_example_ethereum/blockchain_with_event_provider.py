from djwebdapp.models import Blockchain

blockchain, _ = Blockchain.objects.get_or_create(
    name='Ethereum Local with event provider',
    provider_class='djwebdapp_ethereum.provider.EthereumEventProvider',
    min_confirmations=0,
)

blockchain.node_set.get_or_create(
    endpoint='http://ethlocal:8545',
)
