import binascii
import pytest
import pytezos

from djwebdapp.models import Blockchain

# This comes from the bake.sh script in the tezos container
BOOTSTRAP1_IDENTITY="tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx"
BOOTSTRAP1_PUBLIC="edpkuBknW28nW72KG6RoHtYW7p12T6GKc7nAbwYX5m8Wd9sDVC9yav"
BOOTSTRAP1_SECRET="edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh"

BOOTSTRAP2_IDENTITY="tz1gjaF81ZRRvdzjobyfVNsAeSC6PScjfQwN"
BOOTSTRAP2_PUBLIC="edpktzNbDAUjUk697W7gYg2CRuBQjyPxbEg8dLccYYwKSKvkPvjtV9"
BOOTSTRAP2_SECRET="edsk39qAm1fiMjgmPkw1EgQYkMzkJezLNewd7PLNHTkr6w9XA2zdfo"

BOOTSTRAP3_IDENTITY="tz1faswCTDciRzE4oJ9jn2Vm2dvjeyA9fUzU"
BOOTSTRAP3_PUBLIC="edpkuTXkJDGcFd5nh6VvMz8phXxU3Bi7h6hqgywNFi1vZTfQNnS1RV"
BOOTSTRAP3_SECRET="edsk4ArLQgBTLWG5FJmnGnT689VKoqhXwmDPBuGx3z4cvwU9MmrPZZ"

BOOTSTRAP4_IDENTITY="tz1b7tUupMgCNw2cCLpKTkSD1NZzB5TkP2sv"
BOOTSTRAP4_PUBLIC="edpkuFrRoDSEbJYgxRtLx2ps82UdaYc1WwfS9sE11yhauZt5DgCHbU"
BOOTSTRAP4_SECRET="edsk2uqQB9AY4FvioK2YMdfmyMrer5R8mGFyuaLLFfSRo8EoyNdht3"

BOOTSTRAP5_IDENTITY="tz1ddb9NMYHZi5UzPdzTZMYQQZoMub195zgv"
BOOTSTRAP5_PUBLIC="edpkv8EUUH68jmo3f7Um5PezmfGrRF24gnfLpH3sVNwJnV5bVCxL2n"
BOOTSTRAP5_SECRET="edsk4QLrcijEffxV31gGdN2HU7UpyJjA8drFoNcmnB28n89YjPNRFm"



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


def create_account(blockchain, name, address, secret_key):
    def _secret_key(key):
        exponent = pytezos.Key.from_encoded_key(key).secret_exponent
        return binascii.b2a_base64(exponent).decode()

    return blockchain.account_set.create(
        address=address,
        secret_key=_secret_key(secret_key),
        name=name,
    )


@pytest.fixture
def account1(blockchain):
    return create_account(blockchain, 'account1', BOOTSTRAP1_IDENTITY, BOOTSTRAP1_SECRET)


@pytest.fixture
def account2(blockchain):
    return create_account(blockchain, 'account2', BOOTSTRAP2_IDENTITY, BOOTSTRAP2_SECRET)


@pytest.fixture
def account3(blockchain):
    return create_account(blockchain, 'account3', BOOTSTRAP3_IDENTITY, BOOTSTRAP3_SECRET)


@pytest.fixture
def account4(blockchain):
    return create_account(blockchain, 'account4', BOOTSTRAP4_IDENTITY, BOOTSTRAP4_SECRET)


@pytest.fixture
def account5(blockchain):
    return create_account(blockchain, 'account5', BOOTSTRAP5_IDENTITY, BOOTSTRAP5_SECRET)


@pytest.fixture
@pytest.mark.django_db
def multisig(deploy_and_index, blockchain, account1):
    from djwebdapp_multisig.models import MultisigContract
    multisig_contract = MultisigContract.objects.create(
        admin=account1,
        sender=account1,
    )

    deploy_and_index(multisig_contract)

    assert blockchain.provider.spool() is None

    return multisig_contract
