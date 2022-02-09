import pytest


@pytest.mark.django_db
def test_normalize(include):
    variables = include(
        'djwebdapp_example/ethereum',
        'client', 'deploy', 'blockchain', 'index', 'normalize',
    )

    contract = variables['contract']

    # test subsequent blockchain calls
    hash = variables['client'].eth.contract(
        abi=variables['abi'],
        address=variables['address'],
    ).functions.mint(
        variables['client'].eth.default_account,
        10,
    ).transact()
    variables['client'].eth.wait_for_transaction_receipt(hash)

    assert contract.fa12.balance_set.first().balance == 1000
    contract.blockchain.provider.index()
    assert contract.call_set.count() == 2
    assert contract.fa12.mint_set.count() == 2
    assert contract.fa12.balance_set.first().balance == 1010
