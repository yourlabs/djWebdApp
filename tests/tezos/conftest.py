import binascii
import pytest
import pytezos

from djwebdapp.models import Account, Blockchain


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
@pytest.mark.django_db
def blockchain(head):
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

@pytest.fixture
@pytest.mark.django_db
def alice(blockchain):
    alice, _ = Account.objects.update_or_create(
        blockchain=blockchain,
        address='tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
        defaults=dict(
            secret_key=binascii.b2a_base64(pytezos.Key.from_encoded_key(
                'edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh'
            ).secret_exponent).decode(),
        ),
    )
    return alice
