from djwebdapp_example_ethereum.models import FA12Ethereum, FA12EthereumMint

# create a normalized contract object
contract = FA12Ethereum.objects.create(
    blockchain=blockchain,
    sender=admin,
    token_name='Your Token',
    token_symbol='YT',
)

# make a couple of mint calls
first_mint = FA12EthereumMint.objects.create(
    target_contract=contract,
    sender=admin,
    mint_account=admin,
    mint_amount=100,
)
second_mint = FA12EthereumMint.objects.create(
    target_contract=contract,
    sender=admin,
    mint_account=admin,
    mint_amount=200,
)

# let's deploy each transaction one by one
# run ./manage.py spool in a bash loop instead of doing this in python
import time
while blockchain.provider.spool():
    time.sleep(.1)

contract.refresh_from_db()
print(contract.level, contract.hash, contract.address)

first_mint.refresh_from_db()
print(first_mint.level, first_mint.hash)

second_mint.refresh_from_db()
print(second_mint.level, second_mint.hash)

# Given all these transactions are sent from the same account, each was done in
# a different block to prevent noonce issues
assert contract.level < first_mint.level < second_mint.level
