# create a keyfile, we could have created it with geth account new too
new_account = client.eth.account.create()
keyfile = new_account.encrypt('')

# decode private key and get address
address = Web3.to_checksum_address(keyfile['address'])
private_key = blockchain.provider.client.eth.account.decrypt(keyfile, '')

# send some ether from the seed account
client.eth.send_transaction(dict(
    to=address,
    value=client.to_wei(4_000_000, 'ether'),
))

# wait until the blockchain validates the transfer
import time
while not client.eth.get_balance(address):
    time.sleep(.1)

Contract = client.eth.contract(
    abi=contract.abi,
    address=contract.address,
)

tx = Contract.functions.mint(client.eth.default_account, 300)

nonce = client.eth.get_transaction_count(client.eth.default_account)
options = {
    'from': address,
    'nonce': nonce,
}
options['gas'] = client.eth.estimate_gas(
    tx.build_transaction(options)
)
built = tx.build_transaction(options)
signed_txn = client.eth.account.sign_transaction(
    built,
    private_key=private_key,
)

client.eth.send_raw_transaction(signed_txn.rawTransaction)
mint_hash = client.to_hex(client.keccak(signed_txn.rawTransaction))

blockchain.provider.index()
blockchain.provider.normalize()
