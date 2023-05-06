Contract = client.eth.contract(
    abi=contract.abi,
    address=contract.address,
)

tx = Contract.functions.mint(client.eth.default_account, 300).transact()
receipt = client.eth.wait_for_transaction_receipt(tx)
txhash = receipt['transactionHash'].hex()

blockchain.provider.index()
indexed = blockchain.provider.transaction_class.objects.get(hash=txhash)
assert indexed.args, 2

blockchain.provider.normalize()

normalized = contract.fa12ethereummint_set.get(hash=txhash)
assert normalized.mint_amount == 300
