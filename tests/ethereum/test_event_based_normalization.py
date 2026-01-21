import pytest
import time
from unittest import mock
from hexbytes import HexBytes
from web3.datastructures import AttributeDict
from djwebdapp_ethereum.models import EthereumEvent, EthereumTransaction
from tests.ethereum import call_token_proxy, deploy_token_proxy


def mint_non_indexed_blocks(client, num_blocks=2):
    # create non indexed blocks since wallet
    # non spooled ETH transfers are not indexed.
    for _ in range(num_blocks):
        txhash = client.eth.send_transaction(
            dict(
                to=client.eth.default_account,
                value=client.to_wei(1, "ether"),
            )
        )
        client.eth.wait_for_transaction_receipt(txhash)



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
    fa2_contract = variables['contract']
    client = variables['client']

    fa2_contract.blockchain.min_confirmations = 2
    fa2_contract.blockchain.save()

    # emit non spooled transaction
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
    tx = EthereumTransaction.objects.get(hash=hash.to_0x_hex())
    assert tx.kind == "function"
    assert tx.index is False
    assert tx.transactionevent_set.first().name == "Mint"
    assert tx.state == "confirm"
    assert tx.function == None

    mint_non_indexed_blocks(client)

    # Reindexing should set the correct function name
    fa2_contract.blockchain.provider.index()

    tx.refresh_from_db()
    assert tx.function == "mint"
    assert tx.state == "done"

    blockchain_with_event_provider.refresh_from_db()
    assert (
        blockchain_with_event_provider.index_level
        == blockchain_with_event_provider.provider.head
    )


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

    # create non indexed blocks
    mint_non_indexed_blocks(client)

    # create a spooled mint
    mint = FA12EthereumMint.objects.create(
        target_contract=fa12_contract,
        sender=admin,
        mint_account=admin,
        mint_amount=300,
    )
    mint.deploy()
    mint.refresh_from_db()
    client.eth.wait_for_transaction_receipt(mint.hash)

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
    assert mint.level == admin.blockchain.index_level == admin.blockchain.provider.head

    # we set the `index_level` such that the mint transaction is in a previous
    # block (at state `confirm`).
    admin.blockchain.index_level += 1
    admin.blockchain.save()

    # we mint 2 blocks to save the mint call as `state=done`.
    mint_non_indexed_blocks(client)
    admin.blockchain.provider.index()

    # indexing should start at oldest `confirm` transaction regardless of the
    # `index_level`.
    mint.refresh_from_db()
    assert mint.state == "done"


@pytest.mark.django_db
def test_index_contract_from_block_to_block(include, blockchain_with_event_provider, client):
    variables = include(
        'djwebdapp_example_ethereum',
        'client',
        'blockchain_with_event_provider',
        'account',
        'deploy_model',  # makes 2 mints
    )
    fa2_contract = variables['contract']
    client = variables['client']

    def mint():
        hash = variables['client'].eth.contract(
            abi=fa2_contract.abi,
            address=fa2_contract.address,
        ).functions.mint(
            variables['client'].eth.default_account,
            10,
        ).transact()
        variables['client'].eth.wait_for_transaction_receipt(hash)

    # index a first time normally
    fa2_contract.blockchain.provider.index()
    init_mint_count = 2
    assert EthereumEvent.objects.count() == 2

    # Stop fa2 contract indexation
    fa2_contract.index = False
    fa2_contract.save()

    start_block = fa2_contract.blockchain.provider.head

    mint()

    # download until before to last mint block
    download_until_block = fa2_contract.blockchain.provider.head

    mint()

    # set blockthain to index from head
    fa2_contract.blockchain.index_level = fa2_contract.blockchain.provider.head
    fa2_contract.blockchain.save()

    assert fa2_contract.blockchain.index_level > download_until_block

    # index contract including first mint only
    fa2_contract.blockchain.provider.download(
        fa2_contract.address,
        start_block,
        download_until_block,
    )

    assert EthereumEvent.objects.count() == init_mint_count + 1

    # fa2_contract is still not being indexed
    fa2_contract.refresh_from_db()
    assert fa2_contract.index is False

    # index contract from first to second mint
    fa2_contract.blockchain.provider.download(
        fa2_contract.address,
        download_until_block,
        fa2_contract.blockchain.index_level,
    )

    assert EthereumEvent.objects.count() == init_mint_count + 2

    # ensure we can still index contract normally
    fa2_contract.index = True
    fa2_contract.save()

    mint()

    fa2_contract.blockchain.provider.index()

    assert EthereumEvent.objects.count() == init_mint_count + 3


@pytest.mark.django_db
def test_normalize_old_unconfirmed_blocks(include, blockchain_with_event_provider, client):
    """
    Tests that confirm txs that have a level lower that blockchain.index_level
    are indexed.
    """
    variables = include(
        'djwebdapp_example_ethereum',
        'client',
        'blockchain_with_event_provider',
        'account',
        'deploy_model',
    )

    # Setup 2 confirm blocks
    blockchain_with_event_provider.min_confirmations = 2
    blockchain_with_event_provider.save()

    token = blockchain_with_event_provider.transaction_set.exclude(address=None).first().contract_subclass()

    token_proxy = deploy_token_proxy(token.sender)
    token_proxy.index = False
    token_proxy.save()
    call_token_proxy(token.sender, token_proxy, token)

    # Need to wait spooling before indexing
    time.sleep(1)

    # mint 1 blocks
    mint_non_indexed_blocks(client, num_blocks=1)

    # index, the index level is now greater than `confirm_tx.level`, but the
    # transaction is less than 2 levels deep and so still marked as "confirm"
    blockchain_with_event_provider.provider.index()
    confirm_tx = EthereumEvent.objects.get(transaction__state="confirm").transaction

    confirm_tx.refresh_from_db()
    blockchain_with_event_provider.refresh_from_db()
    assert confirm_tx.level == blockchain_with_event_provider.index_level - 1
    assert confirm_tx.state == "confirm"

    # mint some more blocks
    mint_non_indexed_blocks(client, num_blocks=2)

    # index everything
    blockchain_with_event_provider.provider.index()

    # assert all transactions are now done
    confirm_tx.refresh_from_db()
    assert confirm_tx.state == "done"
    assert set(EthereumEvent.objects.values_list("transaction__state", flat=True)) == {"done"}


@pytest.mark.django_db
def test_index_eip7702_transaction(blockchain_with_event_provider):
    """
    Test that EIP-7702 transactions (type 4) with authorizationList can be
    indexed without JSON serialization errors.

    EIP-7702 transactions contain an authorizationList field with AttributeDict
    objects containing HexBytes values that must be properly serialized to JSON
    when saving transaction metadata.
    """
    import json
    from djwebdapp.models import Account

    # Create a mock EIP-7702 transaction matching real-world structure
    mock_eip7702_tx = AttributeDict({
        'type': 4,
        'chainId': 1,
        'nonce': 313122,
        'gas': 1598073,
        'maxFeePerGas': 2206557853,
        'maxPriorityFeePerGas': 2100000001,
        'to': '0xdb9B1e94B5b69Df7e401DDbedE43491141047dB3',
        'value': 0,
        'accessList': [],
        'authorizationList': [AttributeDict({
            'chainId': 1,
            'address': '0x63c0c19a282a1B52b07dD5a65b58948A07DAE32B',
            'nonce': 27,
            'yParity': 0,
            'r': HexBytes('0x2d63bbb7a01a8605535d7d9e874b369e99701268b1481faa7fb471db84ea4174'),
            's': HexBytes('0x175127b3e8530969fd8f1dab8eb44c3f5b65be4aef0cd786879d803197fcd1fd'),
        })],
        'input': HexBytes('0xcef6d209'),
        'r': HexBytes('0xc886608f7502f2ed03de2b97f1ded9b65559a1a029c7e6c15e9c41cc9b816dbd'),
        's': HexBytes('0x5aaf0cb394865e7219f0d365f2f2f24a1fc446c88b7bf1bfacea6abe880720d0'),
        'yParity': 0,
        'v': 0,
        'hash': HexBytes('0xd9150d6a9ed8a6e55d37124831505353970b81ebe8f1ef9c78fed8c7bf54d52b'),
        'blockHash': HexBytes('0xea7331d6a073ec5139050194e7598c949c2509e46c0f8c26925021a2b1d9b8bd'),
        'blockNumber': 24282106,
        'transactionIndex': 5,
        'from': '0xC066ac5D385419B1A8c43A0E146fA439837a8B8c',
        'gasPrice': 2204639044,
    })

    # Create sender account
    sender, _ = Account.objects.get_or_create(
        address='0xC066ac5D385419B1A8c43A0E146fA439837a8B8c',
        blockchain=blockchain_with_event_provider,
    )

    # Create contract that will be called
    contract = EthereumTransaction.objects.create(
        blockchain=blockchain_with_event_provider,
        address='0xdb9B1e94B5b69Df7e401DDbedE43491141047dB3',
        index=True,
    )

    # Test provider.json() method directly - this is where serialization happens
    provider = blockchain_with_event_provider.provider
    serialized = provider.json(mock_eip7702_tx)

    # The serialized result should be JSON-serializable (this is where the bug manifests)
    # If the fix is not implemented, this will raise:
    # TypeError: Object of type AttributeDict is not JSON serializable
    json_str = json.dumps(serialized)

    # Verify the structure is correct after serialization
    parsed = json.loads(json_str)
    assert 'authorizationList' in parsed
    assert len(parsed['authorizationList']) == 1
    # Verify HexBytes were converted to hex strings
    assert parsed['authorizationList'][0]['r'] == '0x2d63bbb7a01a8605535d7d9e874b369e99701268b1481faa7fb471db84ea4174'
    assert parsed['authorizationList'][0]['s'] == '0x175127b3e8530969fd8f1dab8eb44c3f5b65be4aef0cd786879d803197fcd1fd'
    # Verify top-level HexBytes were converted
    assert parsed['hash'] == '0xd9150d6a9ed8a6e55d37124831505353970b81ebe8f1ef9c78fed8c7bf54d52b'
    assert parsed['input'] == '0xcef6d209'
