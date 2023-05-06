from djwebdapp_ethereum.models import EthereumTransaction

# Create a smart contract to deploy
contract = EthereumTransaction.objects.create(
    sender=bootstrap,
    state='deploy',
    max_fails=2,  # try twice before aborting, to speed up tests!
    bytecode=bytecode,
    abi=abi,
    args=['Your New Token', 'YNT'],
)

# Create a call that should deploy afterwards on that contract
mint = EthereumTransaction.objects.create(
    sender=bootstrap,
    state='deploy',
    max_fails=2,
    contract=contract,
    function='mint',
    args=(
        new_wallet.address,
        1000,
    ),
)

# Spool will first deploy the contract
assert blockchain.provider.spool() == contract

# Get deployment level
contract.refresh_from_db()

# Geth --dev incremented the block level transactionnaly,
# but you'd need that to wait a block on a real network as such
blockchain.wait()

# Now spool will deploy the mint call!
assert blockchain.provider.spool() == mint

# And has nothing else to do
assert not blockchain.provider.spool()
