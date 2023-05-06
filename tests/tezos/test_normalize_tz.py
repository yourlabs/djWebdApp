import pytest


@pytest.mark.django_db
def test_normalize(include, blockchain):
    variables = include(
        'djwebdapp_example_tezos',
        'client', 'load', 'deploy', 'blockchain', 'index', 'normalize',
    )

    contract = variables['contract']

    # test subsequent blockchain calls
    variables['client'].contract(variables['address']).mint(
        'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
        10,
    ).send(min_confirmations=2)

    assert contract.fa12tezosbalance_set.first().balance == 1300
    contract.blockchain.wait_blocks()
    contract.blockchain.provider.index()
    assert contract.call_set.count() == 3
    assert contract.fa12tezosmint_set.count() == 2
    contract.blockchain.provider.normalize()
    assert contract.call_set.count() == 3
    assert contract.fa12tezosmint_set.count() == 3
    assert contract.fa12tezosbalance_set.first().balance == 1310
