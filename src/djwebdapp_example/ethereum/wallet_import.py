# create a keyfile, we could have created it with geth account new too
new_account = client.eth.account.create()
keyfile = new_account.encrypt('')

# decode private key and get address
address = Web3.toChecksumAddress(keyfile['address'])
private_key = blockchain.provider.client.eth.account.decrypt(keyfile, '')

# send some ether from the seed account
client.eth.send_transaction(dict(
    to=address,
    value=client.toWei(1337, 'ether'),
))

# wait until the blockchain validates the transfer
import time
while not client.eth.getBalance(address):
    time.sleep(.1)

# import the freshly created wallet by secret key
from djwebdapp.models import Account
bootstrap = Account.objects.create(
    secret_key=bytes(private_key),
    address=address,
    blockchain=blockchain,
)

# balance was automatically fetched
assert bootstrap.balance == 1337
old_balance = bootstrap.balance
