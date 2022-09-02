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
def test_spool_call_parallel(include):
    include(
        'djwebdapp_example/tezos',
        'client',
        'blockchain',
        'wallet_import',
        '../wallet_create',
        'transfer',
        'load',
        'deploy_contract',
        'call_parallel',
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


@pytest.mark.django_db
@pytest.mark.parametrize('method', ('shell', 'python'))
def test_download(include, method):
    variables = include(
        'djwebdapp_example/tezos',
        'client', 'load', 'deploy', 'blockchain',
    )
    blockchain = variables['blockchain']
    blockchain.wait(blockchain.provider.head + 2)

    # configure the blockchain object for .provider.download method
    blockchain.configuration['tzkt_url'] = 'http://tzkt-api:5000'
    blockchain.save()

    contract, _ = TezosTransaction.objects.get_or_create(
        blockchain=variables['blockchain'],
        address=variables['address'],
    )

    if method == 'python':
        contract.provider.download(target=contract.address)
    elif method == 'shell':
        management.call_command(
            'history_download',
            blockchain.name,
            contract.address,
        )

    call = contract.call_set.first()

    assert call
    assert call.function == 'mint'
    assert call.args['_to'] == 'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx'
    assert call.args['value'] == 1000
