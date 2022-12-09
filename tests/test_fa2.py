from django.db.utils import IntegrityError
import pytest
from rest_framework.test import APIClient

from djwebdapp_fa2.models import Fa2Contract, MintCall, UpdateProxyCall


@pytest.mark.django_db
def test_deploy_fa2(wait_transaction, alice, bob, charlie, multisig):
    fa2_contract = Fa2Contract.objects.create(
        sender=alice,
        manager=alice,
        multisig=multisig,
        metadata_uri=f"ipfs://djwebdapp_nft",
    )

    wait_transaction(fa2_contract.origination)

    wait_transaction(fa2_contract.origination.add_authorized_contract_calls.first().transaction)

    client = fa2_contract.sender.provider.client

    fa2_interface = client.contract(fa2_contract.origination.address)
    assert fa2_interface.storage["manager"]() == fa2_contract.manager.address
    assert fa2_interface.storage["multisig"]() == fa2_contract.multisig.origination.address
    assert fa2_interface.storage["metadata"][""]().decode() == fa2_contract.metadata_uri

    update_proxy = UpdateProxyCall.objects.create(
        sender=alice,
        target_contract=fa2_contract,
        proxy=alice
    )
    wait_transaction(update_proxy.transaction)

    mint_call = MintCall.objects.create(
        target_contract=fa2_contract,
        sender=alice,
        owner=alice,
        token_id=0,
        amount=100_000_000,
        metadata_uri=f"ipfs://djwebdapp_nft_1",
    )
    wait_transaction(mint_call.transaction)

    #fa2_interface.mint(mint_param).send(min_confirmations=2)
    alice.blockchain.provider.index()

    assert fa2_contract.fa2token_set.count() == 1
    assert fa2_contract.fa2token_set.first().token_id == 0

    assert fa2_contract.fa2token_set.first().balance_set.count() == 1
    assert fa2_contract.fa2token_set.first().balance_set.first().account == alice
    assert fa2_contract.fa2token_set.first().balance_set.first().amount == 100_000_000

    transfer_param = [{
        "from_": alice.address,
        "txs": [
            {
                "to_": bob.address,
                "token_id": 0,
                "amount": 1,
            },
            {
                "to_": charlie.address,
                "token_id": 0,
                "amount": 2,
            },
        ],
    }]

    fa2_interface.transfer(transfer_param).send(min_confirmations=2)
    alice.blockchain.provider.index()

    assert fa2_contract.fa2token_set.first().balance_set.count() == 3
    assert fa2_contract.fa2token_set.first().balance_set.first().account == alice
    assert fa2_contract.fa2token_set.first().balance_set.first().amount == 99999997
    assert fa2_contract.fa2token_set.first().balance_set.filter(account=bob).first().amount == 1
    assert fa2_contract.fa2token_set.first().balance_set.filter(account=charlie).first().amount == 2

    burn_param = {
        "token_id": 0,
        "token_amount": 1,
    }

    fa2_interface.burn(burn_param).send(min_confirmations=2)
    alice.blockchain.provider.index()

    assert fa2_contract.fa2token_set.first().balance_set.filter(account=alice).first().amount == 99999996
