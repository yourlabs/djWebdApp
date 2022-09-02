# Then, insert a smart contract with our address
from djwebdapp_ethereum.models import EthereumTransaction
contract = EthereumTransaction.objects.create(
    blockchain=blockchain,
    # used to index method calls
    address=address,
    # used to translate function calls
    abi=abi,
    # used to fill the contract metadata
    hash=contract_hash.hex(),
)
assert contract.kind == 'contract'

# But calls have not yet been synchronized
assert not contract.call_set.count()

# Let's index the blockchain, you could also run ./manage.py index
blockchain.provider.index()

# Refresh our contract model object
contract.refresh_from_db()

# Gas cost was indexed
assert contract.gas


# Mint call was indexed
call = contract.call_set.first()
assert call.function == 'mint'
assert call.args['amount'] == 1000
