# First, we need to add a blockchain in the database
from djwebdapp.models import Blockchain
blockchain, _ = Blockchain.objects.get_or_create(
    name='Tezos Local',
    provider_class='djwebdapp_tezos.provider.TezosProvider',
    min_confirmations=2,  # two blocks to be safe from reorgs
)

# Add our node to the blockchain
blockchain.node_set.get_or_create(endpoint='http://tzlocal:8732')
