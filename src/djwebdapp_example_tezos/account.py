from djwebdapp.models import Account

# Given a blockchain and no address, djwebdapp will create a keypair
admin = Account.objects.create(blockchain=blockchain, name='Admin')

# Now, provision this wallet with some xtz from the default client wallet
client.transaction(
    destination=admin.address,
    amount=1_000_000,
).autofill().sign().inject(_async=False)

# Wait until the account receives the balance
while not admin.balance:
    admin.refresh_balance()
