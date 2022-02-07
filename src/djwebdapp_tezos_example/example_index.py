from djwebdapp.models import Blockchain, SmartContract

# First, we need to add a blockchain in the database
blockchain, _ = Blockchain.objects.get_or_create(
    name='Tezos Local',
    provider_class='djwebdapp_tezos.provider.TezosProvider',
)

# Add our node to the blockchain
blockchain.node_set.get_or_create(endpoint='http://tzlocal:8732')

# Then, insert a smart contract with our address
contract, _ = SmartContract.objects.get_or_create(
    blockchain=blockchain,
    address=address,  # noqa it's a global
)

# in the case of tezos, you could also run ./manage.py tzkt_index_contracts
blockchain.provider.index()
contract.refresh_from_db()

# indexed Call objects:
assert contract.call_set.count()
