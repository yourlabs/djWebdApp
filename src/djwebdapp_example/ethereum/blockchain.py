# First, we need to add a blockchain in the database
from djwebdapp.models import Blockchain
blockchain, _ = Blockchain.objects.get_or_create(
    name='Ethereum Local',
    provider_class='djwebdapp_ethereum.provider.EthereumProvider',
)

# Add our node to the blockchain
blockchain.node_set.get_or_create(endpoint='http://ethlocal:8545')
