import json
import copy
import pytest

from django.core import management
from djwebdapp.models import Blockchain
from djwebdapp_tezos.models import TezosTransaction

from pytezos import pytezos
from pytezos import ContractInterface
from pytezos.contract.result import OperationResult


@pytest.mark.django_db
def test_index(include):
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
def test_confirm(include):
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


def cross_contract_call_factory():
    using_params = dict(
        key='edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh',
        shell='http://tzlocal:8732',
    )

    callee_micheline = json.load(open('src/djwebdapp_example/tezos/callee.json'))
    caller_micheline = json.load(open('src/djwebdapp_example/tezos/caller.json'))

    callee_ci = ContractInterface.from_micheline(callee_micheline).using(**using_params)
    callee_init_storage = {
        "counter": 0,
        "price": 100,
    }
    opg = callee_ci.originate(initial_storage=callee_init_storage).send(min_confirmations=1)
    callee_addr = OperationResult.from_operation_group(opg.opg_result)[
        0
    ].originated_contracts[0]
    callee_ci = pytezos.using(**using_params).contract(callee_addr)

    caller_ci = ContractInterface.from_micheline(caller_micheline).using(**using_params)
    caller_init_storage = caller_ci.storage.dummy()
    caller_init_storage["callee"] = callee_ci.address
    opg = caller_ci.originate(initial_storage=caller_init_storage).send(min_confirmations=1)
    caller_addr = OperationResult.from_operation_group(opg.opg_result)[
        0
    ].originated_contracts[0]
    caller_ci = pytezos.using(**using_params).contract(caller_addr)

    return caller_ci, callee_ci


@pytest.mark.django_db
def test_inter_contract_calls():
    caller_ci, callee_ci = cross_contract_call_factory()

    op = caller_ci.set_counter({"new_counter": 10, "price": 100}).with_amount(100).send(min_confirmations=2)

    blockchain, _ = Blockchain.objects.get_or_create(
        name='Tezos Local',
        provider_class='djwebdapp_tezos.provider.TezosProvider',
    )

    # Add our node to the blockchain
    blockchain.node_set.get_or_create(endpoint='http://tzlocal:8732')

    caller = TezosTransaction.objects.create(
        blockchain=blockchain,
        address=caller_ci.address,
    )

    caller.blockchain.provider.index()

    caller_set_counter = TezosTransaction.objects.filter(contract__address=caller_ci.address, function="set_counter").first()
    callee_set_counter = TezosTransaction.objects.filter(contract__address=callee_ci.address, function="set_counter").first()
    caller_callback_set_counter = TezosTransaction.objects.filter(contract__address=caller_ci.address, function="set_counter_callback").first()

    assert caller_set_counter.nonce == None
    assert callee_set_counter.nonce == 0
    assert caller_callback_set_counter.nonce == 1

    assert caller_set_counter.args == {"new_counter": 10, "price": 100}
    assert callee_set_counter.args == 10
    assert caller_callback_set_counter.args == 10

    assert caller_set_counter.amount == 100
    assert callee_set_counter.amount == 100
    assert caller_callback_set_counter.amount == 100

    assert caller_set_counter.hash == callee_set_counter.hash == caller_callback_set_counter.hash


@pytest.mark.django_db
def test_inter_contract_calls_bulk():
    caller_ci, callee_ci = cross_contract_call_factory()

    using_params = dict(
        key='edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh',
        shell='http://tzlocal:8732',
    )
    op = pytezos.using(**using_params).bulk(
        caller_ci.set_counter({"new_counter": 10, "price": 100}).with_amount(100),
        caller_ci.set_counter({"new_counter": 20, "price": 100}).with_amount(100),
    ).send(min_confirmations=2)

    blockchain, _ = Blockchain.objects.get_or_create(
        name='Tezos Local',
        provider_class='djwebdapp_tezos.provider.TezosProvider',
    )

    # Add our node to the blockchain
    blockchain.node_set.get_or_create(endpoint='http://tzlocal:8732')

    caller = TezosTransaction.objects.create(
        blockchain=blockchain,
        address=caller_ci.address,
    )

    caller.blockchain.provider.index()

    caller_set_counter_qs = TezosTransaction.objects.filter(contract__address=caller_ci.address, function="set_counter").order_by("created_at")
    callee_set_counter_qs = TezosTransaction.objects.filter(contract__address=callee_ci.address, function="set_counter").order_by("created_at")
    caller_callback_set_counter_qs = TezosTransaction.objects.filter(contract__address=caller_ci.address, function="set_counter_callback").order_by("created_at")

    caller_set_counter = caller_set_counter_qs.first()
    callee_set_counter = callee_set_counter_qs.first()
    caller_callback_set_counter = caller_callback_set_counter_qs.first()

    hash = caller_set_counter.hash
    assert caller_set_counter.hash == callee_set_counter.hash == caller_callback_set_counter.hash

    assert caller_set_counter.nonce == None
    assert callee_set_counter.nonce == 0
    assert caller_callback_set_counter.nonce == 1

    assert caller_set_counter.args == {"new_counter": 10, "price": 100}
    assert callee_set_counter.args == 10
    assert caller_callback_set_counter.args == 10

    assert caller_set_counter.amount == 100
    assert callee_set_counter.amount == 100
    assert caller_callback_set_counter.amount == 100

    caller_set_counter = caller_set_counter_qs.last()
    callee_set_counter = callee_set_counter_qs.last()
    caller_callback_set_counter = caller_callback_set_counter_qs.last()

    assert caller_set_counter.nonce == None
    assert callee_set_counter.nonce == 2
    assert caller_callback_set_counter.nonce == 3

    assert caller_set_counter.args == {"new_counter": 20, "price": 100}
    assert callee_set_counter.args == 20
    assert caller_callback_set_counter.args == 20

    assert caller_set_counter.amount == 100
    assert callee_set_counter.amount == 100
    assert caller_callback_set_counter.amount == 100

    assert caller_set_counter.hash == callee_set_counter.hash == caller_callback_set_counter.hash == hash
