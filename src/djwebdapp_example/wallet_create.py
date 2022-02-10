# create a new wallet on that blockchain, secret key auto generates
new_wallet = Account.objects.create(blockchain=blockchain)
assert new_wallet.balance == 0
