import pytest

from djwebdapp_multisig.models import AddAuthorizedContractCall, MultisigContract


@pytest.mark.django_db
def test_deploy_multisig(wait_transaction, alice):
    multisig_contract = MultisigContract.objects.create(
        admin=alice,
        sender=alice,
    )

    wait_transaction(multisig_contract.origination)

    client = multisig_contract.sender.provider.client
    client.contract(multisig_contract.origination.address)

    multisig_interface = client.contract(multisig_contract.origination.address)
    assert multisig_interface.storage["admins"]() == [multisig_contract.admin.address]


@pytest.mark.django_db
def test_add_authorized_contract(wait_transaction, alice):
    multisig_contract = MultisigContract.objects.create(
        admin=alice,
        sender=alice,
    )

    wait_transaction(multisig_contract.origination)

    add_authorized_contract_call = AddAuthorizedContractCall.objects.create(
        sender=alice,
        target_contract=multisig_contract,
        contract_to_authorize=multisig_contract.origination,
    )

    wait_transaction(add_authorized_contract_call.transaction)

    client = multisig_contract.sender.provider.client
    multisig_interface = client.contract(multisig_contract.origination.address)
    assert multisig_interface.storage["authorized_contracts"]() == [multisig_contract.origination.address]
