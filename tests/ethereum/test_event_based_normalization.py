import pytest

from tests.ethereum.conftest import blockchain


def get_contract_events(contract_abi):
    events = []
    for entry in contract_abi:
        if "type" in entry and entry["type"] == "event" and "name" in entry:
            events.append(entry["name"])
    return events


from djwebdapp_ethereum.models import EthereumEvent, EthereumTransaction
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
def test_normalize(include, blockchain, client):
    variables = include(
        'djwebdapp_example_ethereum',
        'client',
        'blockchain',
        'account',
        'deploy_model',
    )

    token = blockchain.transaction_set.exclude(address=None).first().contract_subclass()
    token_proxy = deploy_token_proxy(token.sender)
    call_token_proxy(token.sender, token_proxy, token)

    blockchain.provider.index()
    assert EthereumEvent.objects.count() == 5
    assert EthereumEvent.objects.filter(contract=token_proxy).count() == 2
    assert EthereumEvent.objects.filter(contract=token).count() == 3
