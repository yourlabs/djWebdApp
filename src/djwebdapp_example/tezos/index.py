# Insert a smart contract with our address
from djwebdapp_tezos.models import TezosTransaction
contract = TezosTransaction.objects.create(
    blockchain=blockchain,
    address=address,
)

# Transaction kind was setup automatically
assert contract.kind == 'contract'

# Unspecified, micheline was downloaded automatically
assert contract.micheline

# But calls have not yet been synchronized
assert not contract.call_set.count()

# Let's index the blockchain
# in the case of tezos, you could also run ./manage.py tzkt_index_contracts
blockchain.provider.index()

# Refresh our contract model object
contract.refresh_from_db()

# Gas cost was indexed
assert contract.gas

# Mint call was indexed
call = contract.call_set.first()
assert call.function == 'mint'
assert call.args['value'] == 1000
