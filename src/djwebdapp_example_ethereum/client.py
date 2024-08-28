from web3 import Web3

# use local blockchain with default account
client = Web3(Web3.HTTPProvider('http://ethlocal:8545'))
client.eth.default_account = client.eth.accounts[0]

# enable support for geth --dev sandbox
from web3.middleware import ExtraDataToPOAMiddleware
client.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
