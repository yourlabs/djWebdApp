from django.db.utils import IntegrityError
import pytest
from rest_framework.test import APIClient

from djwebdapp_fa2.models import Fa2Contract, MintCall, UpdateProxyCall
from djwebdapp_multisig.models import AddAuthorizedContractCall


@pytest.mark.django_db
def test_deploy_fa2(deploy_and_index, account1, account2, account3, multisig):
    fa2_contract = Fa2Contract.objects.create(
        sender=account1,
        manager=account1,
        multisig=multisig,
        metadata_uri=f"ipfs://djwebdapp_nft",
        state="deploy",
    )

    fa2_call = AddAuthorizedContractCall.objects.create(
        sender=fa2_contract.sender,
        contract_to_authorize=fa2_contract,
        contract=fa2_contract.multisig,
        state="deploy",
    )

    assert fa2_contract == fa2_contract.blockchain.provider.spool()
    fa2_contract.blockchain.wait()
    fa2_contract.blockchain.provider.index()
    assert fa2_call == fa2_contract.blockchain.provider.spool()


    client = fa2_contract.sender.provider.client

    fa2_contract.refresh_from_db()
    fa2_interface = client.contract(fa2_contract.address)
    assert fa2_interface.storage["manager"]() == fa2_contract.manager.address
    assert fa2_interface.storage["multisig"]() == fa2_contract.multisig.address
    assert fa2_interface.storage["metadata"][""]().decode() == fa2_contract.metadata_uri

    update_proxy = UpdateProxyCall.objects.create(
        sender=account1,
        contract=fa2_contract,
        proxy=account1,
        state='deploy',
    )

    mint_call = MintCall.objects.create(
        contract=fa2_contract,
        sender=account1,
        owner=account1,
        token_id=0,
        token_amount=100_000_000,
        metadata_uri=f"ipfs://djwebdapp_nft_1",
        state='deploy',
    )
    mint_call.dependency_add(update_proxy)

    update_proxy.blockchain.wait_blocks()
    assert update_proxy == update_proxy.blockchain.provider.spool()
    update_proxy.blockchain.wait()
    update_proxy.blockchain.provider.index()
    assert mint_call == update_proxy.blockchain.provider.spool()
    update_proxy.blockchain.wait()
    update_proxy.blockchain.provider.index()

    #fa2_interface.mint(mint_param).send(min_confirmations=2)
    account1.blockchain.provider.index()
    account1.blockchain.provider.normalize()

    assert fa2_contract.fa2token_set.count() == 1
    assert fa2_contract.fa2token_set.first().token_id == 0

    assert fa2_contract.fa2token_set.first().balance_set.count() == 1
    assert fa2_contract.fa2token_set.first().balance_set.first().account == account1
    assert fa2_contract.fa2token_set.first().balance_set.first().amount == 100_000_000

    transfer_param = [{
        "from_": account1.address,
        "txs": [
            {
                "to_": account2.address,
                "token_id": 0,
                "amount": 1,
            },
            {
                "to_": account3.address,
                "token_id": 0,
                "amount": 2,
            },
        ],
    }]

    fa2_interface.transfer(transfer_param).send(min_confirmations=2)
    account1.blockchain.wait_blocks()
    account1.blockchain.provider.index()
    account1.blockchain.provider.normalize()

    assert fa2_contract.fa2token_set.first().balance_set.count() == 3
    assert fa2_contract.fa2token_set.first().balance_set.first().account == account1
    assert fa2_contract.fa2token_set.first().balance_set.first().amount == 99999997
    assert fa2_contract.fa2token_set.first().balance_set.filter(account=account2).first().amount == 1
    assert fa2_contract.fa2token_set.first().balance_set.filter(account=account3).first().amount == 2

    burn_param = {
        "token_id": 0,
        "token_amount": 1,
    }

    fa2_interface.burn(burn_param).send(min_confirmations=2)
    account1.blockchain.wait_blocks()
    account1.blockchain.provider.index()
    account1.blockchain.provider.normalize()

    assert fa2_contract.fa2token_set.first().balance_set.filter(account=account1).first().amount == 99999996
