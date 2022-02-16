import pytest

from django.core import management
from djwebdapp_tezos.models import TezosTransaction


@pytest.mark.django_db
def test_index(include):
    variables = include(
        'djwebdapp_example/tezos',
        'client', 'load', 'deploy', 'blockchain', 'index',
    )
    contract = variables['contract']

    assert contract.call_set.count() == 1

    # test the second case:
    variables['client'].contract(variables['address']).mint(
        'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
        10,
    ).send(min_confirmations=2)

    contract.blockchain.provider.index()
    assert contract.call_set.count() == 2


@pytest.mark.django_db
def test_tzkt(include):
    variables = include(
        'djwebdapp_example/tezos',
        'client', 'load', 'deploy', 'blockchain',
    )

    contract, _ = TezosTransaction.objects.get_or_create(
        blockchain=variables['blockchain'],
        address=variables['address'],
    )

    management.call_command(
        'tzkt_index_contracts',
        tzkt='http://tzkt-api:5000'
    )

    call = contract.call_set.first()

    assert call
    assert call.function == 'mint'
    assert call.args['_to'] == 'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx'
    assert call.args['value'] == '1000'


@pytest.mark.django_db
def test_transfer(include):
    include(
        'djwebdapp_example/tezos',
        'client',
        'blockchain',
        'wallet_import',
        '../wallet_create',
        'transfer',
        '../wait',
        '../balance',
    )


@pytest.mark.django_db
def test_spool(include):
    include(
        'djwebdapp_example/tezos',
        'client',
        'blockchain',
        'wallet_import',
        '../wallet_create',
        'transfer',
        'load',
        'deploy_contract',
    )


@pytest.mark.django_db
def test_docs(include, admin_smoketest):
    include(
        'djwebdapp_example/tezos',
        'client',
        'load',
        'deploy',
        'blockchain',
        'index',
        'normalize',
        'wallet_import',
        '../wallet_create',
        'transfer',
        '../balance',
        'deploy_contract',
    )
    admin_smoketest()
