from djwebdapp_tezos.models import TezosTransaction

# Create a smart contract to deploy
contract = TezosTransaction.objects.create(
    sender=bootstrap,
    state='deploy',
    max_fails=2,  # try twice before aborting, to speed up tests!
    micheline=source,
    args=storage,
)

# Create a call that should deploy afterwards on that contract
mint = TezosTransaction.objects.create(
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

# Waiting for confirmation blocks ...
blockchain.wait()

# Index to fetch contract address
blockchain.provider.index()

# Deploy the mint call on the same block
assert blockchain.provider.spool() == mint

mint.refresh_from_db()

blockchain.wait()
blockchain.provider.index()
