from djwebdapp.models import Account

# Given a blockchain and no address, djwebdapp will create a keypair
admin = Account.objects.create(blockchain=blockchain, name='Admin')

# Now, provision this wallet with some eths from the default client wallet
client.eth.send_transaction(dict(
    to=admin.address,
    value=client.to_wei(4_000_000, 'ether'),
))

# Wait until the account receives the balance
while not admin.balance:
    admin.refresh_balance()
