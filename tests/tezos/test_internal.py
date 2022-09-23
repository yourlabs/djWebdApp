from decimal import Decimal
import pytest

from djwebdapp_tezos.models import TezosTransaction

import functools
from pathlib import Path
import os

from pymich.compiler import Compiler
from pytezos import ContractInterface
from pytezos.contract.result import OperationResult
from pymich.test import ContractLoader


@pytest.fixture
def loader(client):
    loader = ContractLoader.factory('proxy/A.py')
    loader.storage['B'] = client.key.public_key_hash()
    loader.storage['C'] = loader.storage['B']
    loader.storage['admin'] = client.key.public_key_hash()
    return loader


@pytest.fixture
def A(loader, client):
    return loader.deploy(client)


@pytest.fixture
def B(loader, client):
    return loader.deploy(client)


@pytest.fixture
def C(loader, client):
    return loader.deploy(client)


@pytest.fixture
def D(loader, client):
    return loader.deploy(client)


@pytest.fixture
def opgs(A, B, C, D):
    return (
        A.set_B(B.address).send(min_confirmations=1),
        A.set_C(C.address).send(min_confirmations=1),
        B.set_B(D.address).send(min_confirmations=1),
        C.set_C(A.address).send(min_confirmations=1),
        A.call_B_and_C(dict(
            value_b='B',
            value_c='C',
        )).with_amount(1_000).send(min_confirmations=1),
    )


@pytest.mark.django_db
def test_internal(blockchain, A, B, C, D, opgs):
    caller = TezosTransaction.objects.create(
        blockchain=blockchain,
        address=A.address,
    )
    caller.blockchain.wait_blocks()
    caller.blockchain.provider.index()
    result = TezosTransaction.objects.values_list(
        'function', 'args', 'amount', 'index', 'address'
    ).order_by(
        'level', 'counter', 'nonce'
    )
    expected = [
        (None, None, 0, False, C.address),
        (None, None, 0, False, B.address),
        (None, None, 0, False, D.address),
        (None, None, 0, True, A.address),
        ('set_B', B.address, 0, True, None),
        ('set_C', C.address, 0, True, None),
        ('call_B_and_C', {'value_b': 'B', 'value_c': 'C'}, 1_000, True, None),
        ('set_value_B', 'B', 1_000, True, None),
        ('set_value_C', 'C', 0, True, None),
        ('set_value', 'C', 0, True, None),
        ('set_value', 'B', 0, True, None),
        (None, None, 1_000, True, None),
    ]
    assert list(result) == expected


@pytest.mark.django_db
def test_internal_other(blockchain, A, B, C, D, opgs):
    subject = TezosTransaction.objects.create(
        blockchain=blockchain,
        address=B.address,
    )
    subject.blockchain.wait_blocks()
    subject.blockchain.provider.index()
    result = TezosTransaction.objects.values_list(
        'function',
        'args',
        'amount',
        'index',
        'address',
    ).order_by(
        'level', 'counter', 'nonce'
    )
    expected = [
        (None, None, Decimal('0E-18'), False, A.address),
        (None, None, Decimal('0E-18'), False, C.address),
        (None, None, Decimal('0E-18'), False, D.address),
        (None, None, Decimal('0E-18'), True, B.address),
        ('set_B', D.address, Decimal('0E-18'), True, None),
        ('call_B_and_C', {'value_b': 'B', 'value_c': 'C'}, Decimal('1000.000000000000000000'), True, None),
        ('set_value_B', 'B', Decimal('1000.000000000000000000'), True, None),
        ('set_value_C', 'C', Decimal('0E-18'), True, None),
        ('set_value', 'C', Decimal('0E-18'), True, None),
        ('set_value', 'B', Decimal('0E-18'), True, None),
        (None, None, Decimal('1000.000000000000000000'), True, None)
    ]
    assert list(result) == expected
