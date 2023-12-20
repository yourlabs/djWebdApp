import pytest
import time
from unittest import mock
from djwebdapp_ethereum.models import EthereumEvent, EthereumTransaction


def get_contract_events(contract_abi):
    events = []
    for entry in contract_abi:
        if "type" in entry and entry["type"] == "event" and "name" in entry:
            events.append(entry["name"])
    return events


def deploy_token_proxy(sender):
    with (
        open("./src/djwebdapp_example_ethereum/contracts/Caller.bin") as bytecode,
        open("./src/djwebdapp_example_ethereum/contracts/Caller.abi") as abi,
    ):
        contract = EthereumTransaction.objects.create(
            blockchain=sender.blockchain,
            sender=sender,
            state='deploy',
            bytecode=bytecode.read(),
            abi=abi.read(),
            args=[],
        )
    sender.blockchain.provider.spool()
    contract.refresh_from_db()
    return contract

# Create a call that should deploy afterwards on that contract
def call_token_proxy(sender, token_proxy, token):
    EthereumTransaction.objects.create(
        sender=sender,
        state='deploy',
        contract=token_proxy,
        function='mintProxy',
        args=(
            token.address,
            sender.address,
            10,
        ),
    )
    sender.blockchain.provider.spool()


@pytest.mark.django_db
def test_normalize(include, blockchain_with_event_provider, client):
    variables = include(
        'djwebdapp_example_ethereum',
        'client',
        'blockchain_with_event_provider',
        'account',
        'deploy_model',
    )

    token = blockchain_with_event_provider.transaction_set.exclude(address=None).first().contract_subclass()
    token_proxy = deploy_token_proxy(token.sender)
    call_token_proxy(token.sender, token_proxy, token)

    # Need to wait spooling before indexing
    time.sleep(1)

    blockchain_with_event_provider.provider.index()
    assert EthereumEvent.objects.count() == 5
    assert EthereumEvent.objects.filter(contract=token_proxy).count() == 2
    assert EthereumEvent.objects.filter(contract=token).count() == 3


@pytest.mark.django_db
def test_event_normalization(include, blockchain_with_event_provider, client):
    variables = include(
        'djwebdapp_example_ethereum',
        'client',
        'blockchain_with_event_provider',
        'account',
        'deploy_model',
    )

    token = blockchain_with_event_provider.transaction_set.exclude(address=None).first().contract_subclass()
    token_proxy = deploy_token_proxy(token.sender)
    call_token_proxy(token.sender, token_proxy, token)

    assert EthereumEvent.objects.count() == 0

    # Avoid race condition need to wait spooling before indexing
    time.sleep(1)

    blockchain_with_event_provider.provider.index()
    blockchain_with_event_provider.provider.normalize()

    assert EthereumEvent.objects.count() == 5
    assert EthereumEvent.objects.filter(contract=token).count() == 3

    assert EthereumEvent.objects.filter(
        contract=token,
        transaction__function='mint',
    ).count() == 2

    assert EthereumEvent.objects.filter(
        contract=token,
        transaction__function='mintProxy',
    ).count() == 1

    mint_event_from_proxy = EthereumEvent.objects.get(
        contract=token,
        transaction__function='mintProxy',
    )

    assert mint_event_from_proxy.fa12_balance_movements.count() == 1
    assert mint_event_from_proxy.fa12_balance_movements.first().amount == 10

    assert token.fa12ethereumbalance_set.count() == 1
    assert token.fa12ethereumbalance_set.first().balance == 310
