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


import json
from pytezos import pytezos, Key, ContractInterface, Unit
from pytezos.contract.result import OperationResult
from djwebdapp.models import Blockchain, Account
import binascii
def auction_factory():
    using_params = dict(
        key='edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh',
        shell='http://tzlocal:8732',
    )

    auction_micheline = json.load(open('src/djwebdapp_example/tezos/auction.json'))

    auction_ci = ContractInterface.from_micheline(auction_micheline).using(**using_params)
    auction_init_storage = auction_ci.storage.dummy()
    opg = auction_ci.originate(initial_storage=auction_init_storage).send(min_confirmations=1)
    auction_addr = OperationResult.from_operation_group(opg.opg_result)[
        0
    ].originated_contracts[0]
    auction_ci = pytezos.using(**using_params).contract(auction_addr)

    return auction_ci


@pytest.mark.django_db
def test_call_with_amount():
    auction_ci = auction_factory()

    blockchain, _ = Blockchain.objects.get_or_create(
        name='Tezos Local',
        provider_class='djwebdapp_tezos.provider.TezosProvider',
    )

    # Add our node to the blockchain
    blockchain.node_set.get_or_create(endpoint='http://tzlocal:8732')

    auction = TezosTransaction.objects.create(
        blockchain=blockchain,
        address=auction_ci.address,
    )

    alice, _ = Account.objects.update_or_create(
        blockchain=blockchain,
        address='tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
        defaults=dict(
            secret_key=binascii.b2a_base64(Key.from_encoded_key(
                'edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh'
            ).secret_exponent).decode(),
        ),
    )

    bid = TezosTransaction.objects.create(
        contract=auction,
        sender=alice,
        state="deploy",
        function="bid",
        args=[Unit],
        amount=1_000,
    )
    bid.deploy()

    blockchain.provider.index()

    assert auction_ci.storage["bids"][alice.address]() == 1_000
