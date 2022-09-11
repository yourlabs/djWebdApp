import pytest

from pymich.test import ContractLoader

from djwebdapp_tezos.models import TezosTransaction


@pytest.mark.django_db
def test_internal(client, blockchain, using):
    loader = ContractLoader.factory('proxy/A.py')
    loader.storage['B'] = client.key.public_key_hash()
    loader.storage['C'] = loader.storage['B']
    A = loader.deploy(client)
    caller = TezosTransaction.objects.create(
        blockchain=blockchain,
        address=A.interface.address,
    )
    B = loader.deploy(client)
    C = loader.deploy(client)
    D = loader.deploy(client)
    opg1 = A.interface.set_B(B.address).send(min_confirmations=1)
    opg2 = A.interface.set_C(C.address).send(min_confirmations=1)
    # the following 2 should not be indexed
    opg3 = B.interface.set_B(D.address).send(min_confirmations=1)
    opg4 = C.interface.set_C(A.address).send(min_confirmations=1)
    caller.blockchain.provider.index()
    opg5 = A.interface.call_B_and_C(dict(
        value_b='B',
        value_c='C',
    )).send(min_confirmations=1)
    caller.blockchain.wait_blocks()
    caller.blockchain.provider.index()
    result = TezosTransaction.objects.values_list(
        'function', 'args', 'index', 'address',
    ).order_by(
        'level', 'counter', 'nonce'
    )
    expected = [
        (None, None, False, C.address),
        (None, None, False, B.address),
        (None, None, False, D.address),
        (None, None, True, A.address),
        ('set_B', B.address, True, None),
        ('set_C', C.address, True, None),
        ('call_B_and_C', {'value_b': 'B', 'value_c': 'C'}, True, None),
        ('set_value_B', 'B', True, None),
        ('set_value_C', 'C', True, None),
        ('set_value', 'C', True, None),
        ('set_value', 'B', True, None),
    ]
    assert list(result) == expected
