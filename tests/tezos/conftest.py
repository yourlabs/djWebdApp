import pytest
import pytezos


@pytest.fixture
def using():
    return dict(
        key='edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh',
        shell='http://tzlocal:8732',
    )


@pytest.fixture
def client(using):
    return pytezos.pytezos.using(**using)


@pytest.fixture
def head(client):
    return client.shell.head.metadata()['level_info']['level']


@pytest.fixture
def blockchain(head):
    from djwebdapp.models import Blockchain
    blockchain, _ = Blockchain.objects.update_or_create(
        name='Tezos Local',
        provider_class='djwebdapp_tezos.provider.TezosProvider',
        min_confirmations=2,  # two blocks to be safe from reorgs
        defaults=dict(
            index_level=head,
            configuration=dict(tzkt_url='http://tzkt-api:5000'),
        )
    )
    blockchain.node_set.get_or_create(endpoint='http://tzlocal:8732')
    return blockchain
