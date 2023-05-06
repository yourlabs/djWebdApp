# let's mint some sweet tokens
client_mint = client.contract(contract.address).mint(
    'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
    300,
).send(min_confirmations=2)

# should this really be needed?
blockchain.wait_blocks()

blockchain.provider.index()
indexed = blockchain.provider.transaction_class.objects.get(hash=client_mint.hash())
assert indexed.args, dict(
    _to='tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
    value=300,
)

blockchain.provider.normalize()

normalized = contract.fa12tezosmint_set.get(hash=client_mint.hash())
assert normalized.mint_amount == 300

# normalized transaction is a subclass of indexed transaction
assert normalized.tezostransaction_ptr == indexed
