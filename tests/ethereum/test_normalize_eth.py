import pytest


@pytest.mark.django_db
def test_normalize(include, blockchain):
    variables = include(
        'djwebdapp_example_ethereum',
        'client', 'load', 'deploy', 'blockchain', 'index', 'normalize',
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

    assert contract.fa12ethereumbalance_set.first().balance == 1300

    contract.blockchain.provider.index()
    contract.blockchain.provider.normalize()
    assert contract.call_set.count() == 3
    assert contract.fa12ethereummint_set.count() == 3
    assert contract.fa12ethereumbalance_set.first().balance == 1310
