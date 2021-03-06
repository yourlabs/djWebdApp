import pytest

from djwebdapp_ethereum.models import EthereumTransaction


@pytest.mark.django_db
def test_index(include):
    """
    Test documentation scripts.

    See djwebdapp_tezos.tests.test_tezos_index.test_index docstring.
    """
    variables = include(
        'djwebdapp_example/ethereum',
        'client', 'load', 'deploy', 'blockchain', 'index',
    )

    contract = EthereumTransaction.objects.get(address=variables['address'])

    # test the second case:
    hash = variables['client'].eth.contract(
        abi=variables['abi'],
        address=variables['address'],
    ).functions.mint(
        variables['client'].eth.default_account,
        10,
    ).transact()
    variables['client'].eth.wait_for_transaction_receipt(hash)

    contract.blockchain.provider.index()
    assert contract.call_set.count() == 2


@pytest.mark.django_db
def test_transfer(include):
    include(
        'djwebdapp_example/ethereum',
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
        'djwebdapp_example/ethereum',
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
        'djwebdapp_example/ethereum',
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
