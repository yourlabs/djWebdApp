from web3 import Web3

# use local blockchain with default account
client = Web3(Web3.HTTPProvider('http://ethlocal:8545'))
client.eth.default_account = client.eth.accounts[0]
from web3.middleware import geth_poa_middleware
client.middleware_onion.inject(geth_poa_middleware, layer=0)

# actually deploy the contract:
bytecode = open('src/djwebdapp_example/ethereum/FA12.bin', 'r').read()
abi = open('src/djwebdapp_example/ethereum/FA12.abi', 'r').read()

contract = client.eth.contract(abi=abi, bytecode=bytecode)
contract_hash = contract.constructor('Your New Token', 'YNT').transact()
receipt = client.eth.wait_for_transaction_receipt(contract_hash)
address = receipt.contractAddress

# let's mint some sweat YNTs
contract = client.eth.contract(abi=abi, address=address)
hash = contract.functions.mint(client.eth.default_account, 1000).transact()
receipt = client.eth.wait_for_transaction_receipt(hash)
