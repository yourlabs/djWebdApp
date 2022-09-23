import json
import copy
import pytest

from django.core import management
from djwebdapp.models import Blockchain
from djwebdapp_tezos.models import TezosTransaction


@pytest.mark.django_db
def test_index(include, blockchain):
    variables = include(
        'djwebdapp_example/tezos',
        'client', 'load', 'deploy', 'blockchain', 'index',
    )
    contract = variables['contract']
    blockchain = variables['blockchain']

    assert contract.call_set.count() == 1

    # test the second case:
    variables['client'].contract(variables['address']).mint(
        'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
        10,
    ).send(min_confirmations=2)

    # wait a block since we waited for two confirmation blocks
    blockchain.wait()

    contract.blockchain.provider.index()
    assert contract.call_set.count() == 2


@pytest.mark.django_db
def test_transfer(include, blockchain):
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
def test_spool(include, blockchain):
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
def test_confirm(include, blockchain):
    variables = include(
        'djwebdapp_example/tezos',
        'client',
        'blockchain',
        'wallet_import',
        '../wallet_create',
        'transfer',
        'load',
    )
    contract = TezosTransaction.objects.create(
        sender=variables['bootstrap'],
        state='deploy',
        max_fails=2,  # try twice before aborting, to speed up tests!
        micheline=variables['source'],
        args=variables['storage'],
    )

    management.call_command('spool')

    contract.refresh_from_db()
    assert contract.state == 'confirm'

    # let's ensure that this confirm contract is accounted for indexation
    provider = copy.deepcopy(contract.blockchain.provider)
    provider.index_init()
    assert contract in provider.contracts

    # let's ensure it's not accounted for to spool anymore
    provider = copy.deepcopy(contract.blockchain.provider)
    assert contract not in provider.contracts()

    # indexing again after only one block should not change state to done
    contract.blockchain.wait_blocks(1)
    management.call_command('index')
    contract.refresh_from_db()
    assert contract.state == 'confirm'

    # waiting to be on the new head *after* the confirmation blocks to make
    # indexing move state to done
    contract.blockchain.wait()
    management.call_command('index')

    contract.refresh_from_db()
    assert contract.state == 'done'


@pytest.mark.django_db
def test_spool_call_parallel(include, blockchain):
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
def test_docs(include, admin_smoketest, blockchain):
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
def test_download(include, method, blockchain):
    variables = include(
        'djwebdapp_example/tezos',
        'client', 'load', 'deploy', 'blockchain',
    )

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
