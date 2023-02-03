import pytest
import time

from djwebdapp_multisig.models import AddAuthorizedContractCall, MultisigContract


@pytest.mark.django_db
def test_deploy_multisig(deploy_and_index, account1):
    multisig_contract = MultisigContract.objects.create(
        admin=account1,
        sender=account1,
        state='deploy',
    )
    assert multisig_contract.micheline

    time.sleep(5)
    deploy_and_index(multisig_contract)
    time.sleep(5)

    client = multisig_contract.sender.provider.client
    multisig_interface = client.contract(multisig_contract.address)
    assert multisig_interface.storage["admins"]() == [multisig_contract.admin.address]


@pytest.mark.django_db
def test_add_authorized_contract(deploy_and_index, account1):
    multisig_contract = MultisigContract.objects.create(
        admin=account1,
        sender=account1,
        state='deploy',
    )

    time.sleep(5)
    deploy_and_index(multisig_contract)
    time.sleep(5)

    add_authorized_contract_call = AddAuthorizedContractCall.objects.create(
        sender=account1,
        contract=multisig_contract,
        contract_to_authorize=multisig_contract,
        state='deploy',
    )

    time.sleep(5)
    deploy_and_index(add_authorized_contract_call)
    time.sleep(5)

    client = multisig_contract.sender.provider.client
    multisig_interface = client.contract(multisig_contract.address)
    assert multisig_interface.storage["authorized_contracts"]() == [multisig_contract.address]
