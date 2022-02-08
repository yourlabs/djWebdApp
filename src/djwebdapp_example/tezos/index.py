# First, we need to add a blockchain in the database
from djwebdapp.models import Blockchain
blockchain, _ = Blockchain.objects.get_or_create(
    name='Tezos Local',
    provider_class='djwebdapp_tezos.provider.TezosProvider',
)

# Add our node to the blockchain
blockchain.node_set.get_or_create(endpoint='http://tzlocal:8732')

# Then, insert a smart contract with our address
from djwebdapp_tezos.models import TezosTransaction
contract = TezosTransaction.objects.create(
    blockchain=blockchain,
    address=address,
)
assert contract.micheline  # auto-downloaded when not specified
assert contract.kind == 'contract'

# Let's index the blockchain
# in the case of tezos, you could also run ./manage.py tzkt_index_contracts
assert not contract.call_set.count()
blockchain.provider.index()
contract.refresh_from_db()
assert contract.call_set.first().function == 'mint'
