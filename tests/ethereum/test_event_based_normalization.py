import pytest
import time
from unittest import mock
from djwebdapp_ethereum.models import EthereumEvent, EthereumTransaction
from tests.ethereum import call_token_proxy, deploy_token_proxy


def get_contract_events(contract_abi):
    events = []
    for entry in contract_abi:
        if "type" in entry and entry["type"] == "event" and "name" in entry:
            events.append(entry["name"])
    return events


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
def test_index_event_with_not_spooled_transaction(include, blockchain_with_event_provider, client):
    variables = include(
        'djwebdapp_example_ethereum',
        'client',
        'blockchain_with_event_provider',
        'account',
        'deploy_model',
    )

    # emit non spooled transaction
    fa2_contract = variables['contract']
    hash = variables['client'].eth.contract(
        abi=fa2_contract.abi,
        address=fa2_contract.address,
    ).functions.mint(
        variables['client'].eth.default_account,
        10,
    ).transact()
    variables['client'].eth.wait_for_transaction_receipt(hash)

    fa2_contract.blockchain.provider.index()

    # ensure that transaction is indexed with correct kind
    # and that its mint event FK is set.
    assert fa2_contract.kind == "contract"
    assert fa2_contract.index is True
    tx = EthereumTransaction.objects.get(hash=hash.hex())
    assert tx.kind == "function"
    assert tx.index is False
    assert tx.transactionevent_set.first().name == "Mint"


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


@pytest.mark.django_db
def test_index_eth_spooled_tx(include, blockchain):
    """
    Spooled transactions will take the blockchain level at which the transaction was
    spooled. The indexer will then retrieve the blocks at these levels to look for the
    transaction. However, it is possible that the transaction remains in the mempool
    for longer. In this case, the indexer should update the transaction level to the
    on the transaction was mined into.

    The transaction should remain in `confirm` state if it was not yet confirmed. The
    indexer should keep on indexing from the lowest `confirm` transaction even if
    its `index_level` is higher.
    """
    from djwebdapp_example_ethereum.models import FA12EthereumMint

    variables = include(
        'djwebdapp_example_ethereum',
        'client',
        'blockchain_with_event_provider',
        'account',
        'deploy_model',
    )

    admin = variables["admin"]
    fa12_contract = variables["contract"]
    client = variables["client"]

    # set confirmation blocks
    admin.blockchain.min_confirmations = 2
    admin.blockchain.save()

    # index blockchain to setup `index_level`
    admin.blockchain.provider.index()

    def mint_non_indexed_blocks(num_blocks=2):
        # create non indexed blocks since wallet
        # non spooled ETH transfers are not indexed.
        for _ in range(num_blocks):
            client.eth.send_transaction(
                dict(
                    to=admin.address,
                    value=client.to_wei(1, "ether"),
                )
            )

    # create non indexed blocks
    mint_non_indexed_blocks()

    # create a spooled mint
    mint = FA12EthereumMint.objects.create(
        target_contract=fa12_contract,
        sender=admin,
        mint_account=admin,
        mint_amount=300,
    )
    mint.deploy()
    mint.refresh_from_db()

    # Set level of mint transaction to the previous block (with is non indexed).
    # This simulates a transaction staying in the mempool before being minted
    # leading to a `mint.level` that does not correspond to what is on chain.
    mint.level -= 1
    mint.save()

    # simulate starting to index from the early block saved by djwebdapp
    # (which does not contain the mint transaction since its in the next one).
    admin.blockchain.index_level = mint.level
    admin.blockchain.save()

    admin.blockchain.provider.index()

    admin.blockchain.refresh_from_db()
    mint.refresh_from_db()


    # transaction is still in `confirm` state since we need
    # 2 confirmation blocks.
    assert mint.state == "confirm"
    # we've indexed up to the most recent transaction (the mint call),
    # so both levels should be identical.
    assert admin.blockchain.index_level == mint.level

    # we set the `index_level` such that the mint transaction is in a previous
    # block (at state `confirm`).
    admin.blockchain.index_level += 1
    admin.blockchain.save()

    # we mint 2 blocks to save the mint call as `state=done`.
    mint_non_indexed_blocks()
    admin.blockchain.provider.index()

    # indexing should start at oldest `confirm` transaction regardless of the
    # `index_level`.
    mint.refresh_from_db()
    assert mint.state == "done"
