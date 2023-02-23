import pytest

from djwebdapp_fa2.models import Fa2Contract
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