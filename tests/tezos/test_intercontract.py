import json
import pytest

from djwebdapp_tezos.models import TezosTransaction

from pytezos import pytezos
from pytezos import ContractInterface
from pytezos.contract.result import OperationResult


def cross_contract_call_factory(blockchain):
    using_params = dict(
        key='edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh',
        shell='http://tzlocal:8732',
    )

    callee_micheline = json.load(open('src/djwebdapp_example_tezos/callee.json'))
    caller_micheline = json.load(open('src/djwebdapp_example_tezos/caller.json'))

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
def test_inter_contract_calls(blockchain):
    caller_ci, callee_ci = cross_contract_call_factory(blockchain)

    op = caller_ci.set_counter({"new_counter": 10, "price": 100}).with_amount(100).send(min_confirmations=2)

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

    assert caller_set_counter.nonce == -1
    assert callee_set_counter.nonce == 0
    assert caller_callback_set_counter.nonce == 1

    assert caller_set_counter.args == {"new_counter": 10, "price": 100}
    assert callee_set_counter.args == 10
    assert caller_callback_set_counter.args == 10

    assert caller_set_counter.amount == 100
    assert callee_set_counter.amount == 100
    assert caller_callback_set_counter.amount == 100

    assert caller_set_counter.hash == callee_set_counter.hash == caller_callback_set_counter.hash

    caller_set_counter.internal_calls
    assert caller_set_counter.internal_calls.first() == callee_set_counter
    assert callee_set_counter.internal_calls.first() == caller_callback_set_counter
    assert caller_callback_set_counter.internal_calls.first() == None


@pytest.mark.django_db
def test_inter_contract_calls_bulk(blockchain):
    caller_ci, callee_ci = cross_contract_call_factory(blockchain)

    using_params = dict(
        key='edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh',
        shell='http://tzlocal:8732',
    )
    op = pytezos.using(**using_params).bulk(
        caller_ci.set_counter({"new_counter": 10, "price": 100}).with_amount(100),
        caller_ci.set_counter({"new_counter": 20, "price": 100}).with_amount(100),
    ).send(min_confirmations=2)

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

    assert caller_set_counter.nonce == -1
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

    assert caller_set_counter.nonce == -1
    assert callee_set_counter.nonce == 2
    assert caller_callback_set_counter.nonce == 3

    assert caller_set_counter.args == {"new_counter": 20, "price": 100}
    assert callee_set_counter.args == 20
    assert caller_callback_set_counter.args == 20

    assert caller_set_counter.amount == 100
    assert callee_set_counter.amount == 100
    assert caller_callback_set_counter.amount == 100

    assert caller_set_counter.hash == callee_set_counter.hash == caller_callback_set_counter.hash == hash
