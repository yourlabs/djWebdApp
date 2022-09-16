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
