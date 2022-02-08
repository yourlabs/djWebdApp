import pytest


@pytest.mark.django_db
def test_normalize(include):
    variables = {}
    include('djwebdapp_example/tezos/deploy.py', variables)
    include('djwebdapp_example/tezos/index.py', variables)
    include('djwebdapp_example/tezos/normalize.py', variables)

    contract = variables['contract']

    # test subsequent blockchain calls
    variables['client'].contract(variables['address']).mint(
        'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
        10,
    ).send(min_confirmations=2)

    assert contract.fa12.balance_set.first().balance == 1000
    contract.blockchain.provider.index()
    assert contract.call_set.count() == 2
    assert contract.fa12.mint_set.count() == 2
    assert contract.fa12.balance_set.first().balance == 1010
