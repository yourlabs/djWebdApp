import pytest

from djwebdapp_fa2.models import (
    Fa2Contract,
    MintCall,
)
from djwebdapp_multisig.models import MultisigContract
from djwebdapp_tezos.models import TezosTransaction


@pytest.fixture
def fa2_contract(multisig, account1):
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
    return fa2_contract


@pytest.mark.django_db
def test_update_or_create_overrided_for_tezos_contract(multisig, account1, account2, fa2_contract):
    fa2_origination = TezosTransaction.objects.filter(
        address=fa2_contract.address,
    ).first()

    fa2_contract_modified, created = Fa2Contract.objects.update_or_create(
        tezostransaction_ptr=fa2_origination,
        defaults=dict(
            metadata_uri=f"ipfs://djwebdapp_nft_modified",
            manager=account2,
        ),
    )

    fa2_contract.refresh_from_db()

    assert created is False
    assert fa2_contract.manager == account2
    assert fa2_contract.metadata_uri == fa2_contract_modified.metadata_uri

    # Delete the fa2 contract to force going through the creation case in the
    # next update_or_create call
    fa2_contract_modified.delete(keep_parents=True)

    # No we will create a new fa2 contract with the same address
    fa2_contract_new, created = Fa2Contract.objects.update_or_create(
        tezostransaction_ptr=fa2_origination,
        defaults=dict(
            metadata_uri=f"ipfs://djwebdapp_nft_modified",
            multisig=multisig,
        ),
    )

    assert created is True
    assert not fa2_contract_new.manager
    assert fa2_contract_new.multisig == multisig
    assert fa2_contract_new.tezostransaction_ptr == fa2_origination
    assert Fa2Contract.objects.count() == 1
    assert fa2_contract_new.pk != fa2_contract_modified.pk


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

    # Delete multisig_contract and run the same get_or_create call with another
    # account to ensure the creation case still works as well
    multisig_contract.delete(keep_parents=True)

    # Use account2 to test created
    multisig_new, created = MultisigContract.objects.get_or_create(
        tezostransaction_ptr=multisig_origination,
        admin=account2,
    )

    assert created is True
    assert multisig_new.admin == account2
    assert multisig_new.tezostransaction_ptr == multisig_origination
    assert MultisigContract.objects.count() == 1
    assert multisig_new.pk != multisig_contract.pk
