# Use the transaction model with an amount argument to transfer coins
from djwebdapp.models import Transaction
transaction = Transaction.objects.create(
    name='Provision 10 coins',
    amount=10,
    sender=bootstrap,
    receiver=new_wallet,
    blockchain=blockchain,
)

# Deploy the transaction now
transaction.deploy()
