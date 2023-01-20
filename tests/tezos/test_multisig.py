import pytest

from djwebdapp_multisig.models import AddAuthorizedContractCall, MultisigContract


@pytest.mark.django_db
def test_deploy_multisig(deploy_and_index, account1):
    multisig_contract = MultisigContract.objects.create(
        admin=account1,
        sender=account1,
    )

    deploy_and_index(multisig_contract.origination)

    client = multisig_contract.sender.provider.client
    multisig_interface = client.contract(multisig_contract.origination.address)
    assert multisig_interface.storage["admins"]() == [multisig_contract.admin.address]


@pytest.mark.django_db
def test_add_authorized_contract(deploy_and_index, account1):
    multisig_contract = MultisigContract.objects.create(
        admin=account1,
        sender=account1,
    )

    deploy_and_index(multisig_contract.origination)

    add_authorized_contract_call = AddAuthorizedContractCall.objects.create(
        sender=account1,
        target_contract=multisig_contract,
        contract_to_authorize=multisig_contract.origination,
    )

    deploy_and_index(add_authorized_contract_call.transaction)

    client = multisig_contract.sender.provider.client
    multisig_interface = client.contract(multisig_contract.origination.address)
    assert multisig_interface.storage["authorized_contracts"]() == [multisig_contract.origination.address]
