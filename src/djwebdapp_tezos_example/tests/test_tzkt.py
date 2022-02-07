import pytest

from django.core import management
from djwebdapp.models import Blockchain, SmartContract


@pytest.mark.django_db
def test_tzkt():
    from djwebdapp_tezos_example.example_origination import deploy
    address = deploy()

    blockchain, _ = Blockchain.objects.get_or_create(
        name='Tezos Local',
        provider_class='djwebdapp_tezos.provider.TezosProvider',
    )

    contract, _ = SmartContract.objects.get_or_create(
        blockchain=blockchain,
        address=address,
    )

    management.call_command(
        'tzkt_index_contracts',
        tzkt='http://tzkt-api:5000'
    )

    call = contract.call_set.first()

    assert call
    assert call.function == 'mint'
    assert call.args['_to'] == 'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx'
    assert call.args['value'] == '1000'

    # normalized data also synchronized
    assert contract.fa12
    mint = contract.fa12.mint_set.first()
    assert mint.value == 1000
    assert mint.user.username == 'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx'

    from djwebdapp_tezos_example.models import Balance
    assert Balance.objects.first().balance == 1000
