from djwebdapp.models import Blockchain, SmartContract

# First, we need to add a blockchain in the database
blockchain, _ = Blockchain.objects.get_or_create(
    name='Tezos Local',
    provider_class='djwebdapp_tezos.provider.TezosProvider',
    configuration=dict(
        tzkt='http://tzkt-api:5000',
    ),
)

# Then, insert a smart contract with our address
contract, _ = SmartContract.objects.get_or_create(
    blockchain=blockchain,
    address=address,
)
import time

assert contract.sync(tries=100), 'Contract did not sync'

# indexed Call objects:
assert contract.call_set.count()
