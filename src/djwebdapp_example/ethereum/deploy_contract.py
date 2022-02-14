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

# Geth --dev incremented the block level transactionnaly, no need to wait here,
# you would have to wait for the next block with a real network as such:
# blockchain.wait(1)

# Now spool will deploy the mint call!
assert blockchain.provider.spool() == mint