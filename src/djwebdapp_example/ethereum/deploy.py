# actually deploy the contract:
bytecode = open('src/djwebdapp_example/ethereum/FA12.bin', 'r').read()
abi = open('src/djwebdapp_example/ethereum/FA12.abi', 'r').read()

contract = client.eth.contract(abi=abi, bytecode=bytecode)
contract_hash = contract.constructor('Your New Token', 'YNT').transact()
receipt = client.eth.wait_for_transaction_receipt(contract_hash)
address = receipt.contractAddress

# let's mint some sweet YNTs
contract = client.eth.contract(abi=abi, address=address)
hash = contract.functions.mint(client.eth.default_account, 1000).transact()
receipt = client.eth.wait_for_transaction_receipt(hash)
