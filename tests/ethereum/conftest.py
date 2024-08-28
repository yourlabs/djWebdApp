import pytest

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from djwebdapp.models import Blockchain


@pytest.fixture
def client():
    # use local blockchain with default account
    client = Web3(Web3.HTTPProvider('http://ethlocal:8545'))
    client.eth.default_account = client.eth.accounts[0]

    # enable support for geth --dev sandbox
    client.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return client


@pytest.fixture
def head(client):
    return client.eth.get_block_number()


@pytest.fixture
@pytest.mark.django_db
def blockchain(head):
    # First, we need to add a blockchain in the database
    blockchain, _ = Blockchain.objects.get_or_create(
        name='Ethereum Local',
        provider_class='djwebdapp_ethereum.provider.EthereumProvider',
        defaults=dict(
            index_level=head,
            min_confirmations=0,
        ),
    )
    blockchain.node_set.get_or_create(endpoint='http://ethlocal:8545')
    return blockchain


@pytest.fixture
@pytest.mark.django_db
def blockchain_with_event_provider(head):
    blockchain, _ = Blockchain.objects.get_or_create(
        name='Ethereum Local with event provider',
        provider_class='djwebdapp_ethereum.provider.EthereumEventProvider',
        defaults=dict(
            min_confirmations=0,
        ),
    )
    blockchain.node_set.get_or_create(endpoint='http://ethlocal:8545')
    return blockchain
