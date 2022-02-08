# First, we need to add a blockchain in the database
from djwebdapp.models import Blockchain
blockchain, _ = Blockchain.objects.get_or_create(
    name='Ethereum Local',
    provider_class='djwebdapp_ethereum.provider.EthereumProvider',
)

# Add our node to the blockchain
blockchain.node_set.get_or_create(endpoint='http://ethlocal:8545')

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

# Let's index the blockchain
assert not contract.call_set.count()
blockchain.provider.index()

# Refresh our contract model object
contract.refresh_from_db()

# Gas cost was indexed
assert contract.gas

# Mint call was indexed
call = contract.call_set.first()
assert call.function == 'mint'
assert call.args['amount'] == 1000