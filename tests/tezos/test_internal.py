import pytest

from pymich.test import ContractLoader

from djwebdapp_tezos.models import TezosTransaction


@pytest.mark.django_db
def test_internal(client, blockchain, using):
    loader = ContractLoader.factory('proxy/A.py')
    loader.storage['B'] = client.key.public_key_hash()
    loader.storage['C'] = loader.storage['B']
    A = loader.deploy(client)
    B = loader.deploy(client)
    C = loader.deploy(client)
    D = loader.deploy(client)
    opg1 = A.interface.set_B(B.address).send(min_confirmations=1)
    opg2 = A.interface.set_C(C.address).send(min_confirmations=1)
    opg3 = B.interface.set_B(D.address).send(min_confirmations=1)
    opg4 = C.interface.set_C(A.address).send(min_confirmations=1)
    opg5 = A.interface.call_B_and_C(dict(
        value_b='B',
        value_c='C',
    )).send(min_confirmations=1)

    caller = TezosTransaction.objects.create(
        blockchain=blockchain,
        address=A.interface.address,
    )
    caller.blockchain.provider.index()
    breakpoint()
    pass
