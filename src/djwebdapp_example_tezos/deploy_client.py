# let's mint some sweet tokens
client.contract(contract.address).mint(
    'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
    1000,
).send(min_confirmations=2)
