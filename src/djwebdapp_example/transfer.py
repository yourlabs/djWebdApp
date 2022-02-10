# Use the transaction model with an amount argument to transfer coins
from djwebdapp.models import Transaction
transaction = Transaction.objects.create(
    name='Provision 100 XTZ',
    amount=100,
    sender=bootstrap,
    receiver=new_wallet,
    blockchain=blockchain,
)
