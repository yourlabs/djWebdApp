import pytest

from djwebdapp_ethereum.models import EthereumTransaction


@pytest.mark.django_db
def test_index(include, blockchain):
    """
    Test documentation scripts.

    See djwebdapp_tezos.tests.test_tezos_index.test_index docstring.
    """
    variables = include(
        'djwebdapp_example_ethereum',
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
def test_transfer(include, blockchain):
    include(
        'djwebdapp_example_ethereum',
        'client',
        'blockchain',
        'wallet_import',
        '../djwebdapp_example/wallet_create',
        'transfer',
        '../djwebdapp_example/wait',
        '../djwebdapp_example/balance',
    )


@pytest.mark.django_db
def test_spool(include, blockchain):
    include(
        'djwebdapp_example_ethereum',
        'client',
        'blockchain',
        'wallet_import',
        '../djwebdapp_example/wallet_create',
        'transfer',
        'load',
        'deploy_contract',
    )


@pytest.mark.django_db
def test_docs(include, admin_smoketest, blockchain):
    variables = include(
        'djwebdapp_example_ethereum',
        'client',
        'blockchain',
        'account',
        'deploy_model',
        'normalize',
        'wallet_import',
        '../djwebdapp_example/wallet_create',
        'transfer',
        '../djwebdapp_example/balance',
    )
    admin_smoketest()

    # regression test against side against side effect when our
    # Transactions.objects.update_or_create() override creates new objects when
    # it should have updated with parent
    contract = variables['contract']
    assert contract.fa12ethereummint_set.count() == 3
    assert EthereumTransaction.objects.count() == 4

    blockchain.provider.index()

    assert contract.fa12ethereummint_set.count() == 3
    assert EthereumTransaction.objects.count() == 4

    blockchain.provider.normalize()

    assert contract.fa12ethereummint_set.count() == 3
    assert EthereumTransaction.objects.count() == 4
