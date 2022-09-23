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


@pytest.mark.django_db
def test_internal(client, blockchain, using):
    loader = ContractLoader.factory('proxy/A.py')
    loader.storage['B'] = client.key.public_key_hash()
    loader.storage['C'] = loader.storage['B']
    loader.storage['admin'] = client.key.public_key_hash()
    A = loader.deploy(client)
    caller = TezosTransaction.objects.create(
        blockchain=blockchain,
        address=A.address,
    )
    B = loader.deploy(client)
    C = loader.deploy(client)
    D = loader.deploy(client)
    opg1 = A.set_B(B.address).send(min_confirmations=1)
    opg2 = A.set_C(C.address).send(min_confirmations=1)
    # the following 2 should not be indexed
    opg3 = B.set_B(D.address).send(min_confirmations=1)
    opg4 = C.set_C(A.address).send(min_confirmations=1)
    caller.blockchain.provider.index()
    opg5 = A.call_B_and_C(dict(
        value_b='B',
        value_c='C',
    )).with_amount(1_000).send(min_confirmations=1)
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
def test_internal_other(client, blockchain, using):
    loader = ContractLoader.factory('proxy/A.py')
    loader.storage['B'] = client.key.public_key_hash()
    loader.storage['C'] = loader.storage['B']
    loader.storage['admin'] = client.key.public_key_hash()
    A = loader.deploy(client)
    B = loader.deploy(client)
    subject = TezosTransaction.objects.create(
        blockchain=blockchain,
        address=B.address,
    )
    C = loader.deploy(client)
    D = loader.deploy(client)
    opg1 = A.set_B(B.address).send(min_confirmations=1)
    opg2 = A.set_C(C.address).send(min_confirmations=1)
    opg3 = B.set_B(D.address).send(min_confirmations=1)
    opg4 = C.set_C(A.address).send(min_confirmations=1)
    opg5 = A.call_B_and_C(dict(
        value_b='B',
        value_c='C',
    )).with_amount(1_000).send(min_confirmations=1)
    subject.blockchain.wait_blocks()
    subject.blockchain.provider.index()
    result = TezosTransaction.objects.values_list(
        'function', 'args', 'amount', 'index', 'address'
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
