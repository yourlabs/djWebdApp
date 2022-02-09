import pytest

from django.core import management
from djwebdapp.models import Blockchain
from djwebdapp_tezos.models import TezosTransaction


@pytest.mark.django_db
def test_index(include):
    variables = {}
    include('djwebdapp_example/tezos/client.py', variables)
    include('djwebdapp_example/tezos/deploy.py', variables)
    include('djwebdapp_example/tezos/index.py', variables)
    contract = variables['contract']

    assert contract.call_set.count() == 1

    # test the second case:
    variables['client'].contract(variables['address']).mint(
        'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
        10,
    ).send(min_confirmations=2)

    contract.blockchain.provider.index()
    assert contract.call_set.count() == 2


@pytest.mark.django_db
def test_tzkt(include):
    variables = {}
    include('djwebdapp_example/tezos/client.py', variables)
    include('djwebdapp_example/tezos/deploy.py', variables)

    blockchain, _ = Blockchain.objects.get_or_create(
        name='Tezos Local',
        provider_class='djwebdapp_tezos.provider.TezosProvider',
    )

    blockchain.node_set.get_or_create(endpoint='http://tzlocal:8732')

    contract, _ = TezosTransaction.objects.get_or_create(
        blockchain=blockchain,
        address=variables['address'],
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
