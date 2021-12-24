import pytest

from djwebdapp.models import Blockchain, SmartContract


@pytest.mark.django_db
def test_contract_import():
    blockchain = Blockchain.objects.create(
        name='Test blockchain',
        provider_class='djwebdapp.provider.Success',
    )

    contract = SmartContract.objects.create(
        blockchain=blockchain,
        address='f4k34ddr355',
    )

    contract.sync()

    assert contract.hash
    assert contract.sender_id
    assert contract.call_set.count()
