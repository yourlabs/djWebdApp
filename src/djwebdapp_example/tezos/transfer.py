# Use the transaction model with an amount argument to transfer coins
from djwebdapp.models import Transaction
transaction = Transaction.objects.create(
    name='Provision 1.000 coins',
    amount=1_000,
    sender=bootstrap,
    receiver=new_wallet,
    blockchain=blockchain,
)

# Deploy the transaction now
transaction.deploy()

# Wait one block level
transaction.blockchain.wait(transaction.level + 1)

blockchain.provider.index()

new_wallet.refresh_balance()
