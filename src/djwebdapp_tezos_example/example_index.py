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

# in the case of tezos, you could also run ./manage.py tzkt_index_contracts
# or use the following:
from django.core import management
management.call_command('tzkt_index_contracts', tzkt='http://localhost:5000')

#assert contract.sync(tries=100), 'Contract did not sync'

# indexed Call objects:
assert contract.call_set.count()
