# Create a call that should deploy afterwards on that contract
mint_1 = TezosTransaction.objects.create(
    sender=bootstrap,
    state='deploy',
    max_fails=2,
    contract=contract,
    function='mint',
    args=(
        new_wallet.address,
        20,
    ),
)

mint_2 = TezosTransaction.objects.create(
    sender=new_wallet,
    state='deploy',
    max_fails=2,
    contract=contract,
    function='transfer',
    args=[{
        "_from": new_wallet.address,
        "_to": bootstrap.address,
        "value": 10,
    }],
)

new_wallet.provider.get_client().reveal().send(min_confirmations=1)

calls = list(blockchain.provider.spool())
assert calls == [mint_1, mint_2]

for call in calls:
    call.refresh_from_db()

assert calls[0].level == calls[1].level
