import pytest


@pytest.fixture
def blockchain():
    from djwebdapp.models import Blockchain
    blockchain, _ = Blockchain.objects.get_or_create(
        name='Tezos Local',
        provider_class='djwebdapp_tezos.provider.TezosProvider',
        min_confirmations=2,  # two blocks to be safe from reorgs
    )
    blockchain.node_set.get_or_create(endpoint='http://tzlocal:8732')
    return blockchain


@pytest.fixture
def using():
    return dict(
        key='edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh',
        shell='http://tzlocal:8732',
    )


@pytest.fixture
def client(using):
    from pytezos import pytezos
    client = pytezos.using(**using)
    return client
