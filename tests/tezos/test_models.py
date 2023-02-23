import pytest

from djwebdapp_fa2.models import (
    Fa2Contract,
    MintCall,
)
from djwebdapp_multisig.models import MultisigContract
from djwebdapp_tezos.models import TezosTransaction


@pytest.mark.django_db
def test_update_or_create_overrided_for_tezos_contract(multisig, account1, account2):
    fa2_contract = Fa2Contract.objects.create(
        sender=account1,
        manager=account1,
        multisig=multisig,
        metadata_uri=f"ipfs://djwebdapp_nft",
        state="deploy",
    )
    assert fa2_contract == fa2_contract.blockchain.provider.spool()
    fa2_contract.blockchain.wait()
    fa2_contract.blockchain.provider.index()
    fa2_contract.refresh_from_db()

    fa2_origination = TezosTransaction.objects.filter(
        address=fa2_contract.address,
    ).first()

    fa2_contract_modified, created = Fa2Contract.objects.update_or_create(
        tezostransaction_ptr=fa2_origination,
        defaults=dict(
            metadata_uri=f"ipfs://djwebdapp_nft_modified",
        ),
    )

    fa2_contract.refresh_from_db()

    assert created is False
    assert fa2_contract.metadata_uri == fa2_contract_modified.metadata_uri

    # No we will create a new fa2 contract with the same address
    fa2_contract_new, created = Fa2Contract.objects.update_or_create(
        tezostransaction_ptr=fa2_origination,
        manager=account2,
        defaults=dict(
            metadata_uri=f"ipfs://djwebdapp_nft_modified",
            multisig=multisig,
        ),
    )

    assert created is True
    assert fa2_contract_new.manager == account2
    assert fa2_contract_new.multisig == multisig
    assert fa2_contract_new.tezostransaction_ptr == fa2_origination


@pytest.mark.django_db
def test_get_or_create_overrided_for_tezos_contract(multisig, account1, account2):
    multisig_origination = TezosTransaction.objects.filter(
        address=multisig.address,
    ).first()

    multisig_contract, created = MultisigContract.objects.get_or_create(
        tezostransaction_ptr=multisig_origination,
        admin=account1,
    )

    # The instance was created so the variable `created` should be False
    assert created is False
    assert multisig_contract == multisig

    # Now we delete the multisig and try to create it again by get_or_create
    #multisig.delete()
    multisig_new, created = MultisigContract.objects.get_or_create(
        tezostransaction_ptr=multisig_origination,
        admin=account2,
    )

    assert created is True
    assert multisig_new.admin == account2
    assert multisig_new.tezostransaction_ptr == multisig_origination


@pytest.mark.django_db
def test_update_or_create_overrided_for_tezos_call(multisig, account1, account2):
    fa2_contract = Fa2Contract.objects.create(
        sender=account1,
        manager=account1,
        multisig=multisig,
        metadata_uri=f"ipfs://djwebdapp_nft",
        state="deploy",
    )
    assert fa2_contract == fa2_contract.blockchain.provider.spool()
    fa2_contract.blockchain.wait()
    fa2_contract.blockchain.provider.index()
    fa2_contract.refresh_from_db()

    mint_call, _ = MintCall.objects.update_or_create(
        contract=fa2_contract,
        sender=account1,
        owner=account1,
        token_id=0,
        token_amount=10,
        metadata_uri=f"ipfs://djwebdapp_nft_1",
        state='deploy',
    )

    mint_call_modified, created = MintCall.objects.update_or_create(
        tezostransaction_ptr=mint_call,
        defaults=dict(
            metadata_uri=f"ipfs://djwebdapp_nft_1_modified",
        ),
    )

    mint_call.refresh_from_db()

    assert created is False
    assert mint_call.metadata_uri == mint_call_modified.metadata_uri
