import pytest

from django.core import management
from djwebdapp.models import Blockchain
from djwebdapp_tezos.models import TezosTransaction


@pytest.mark.django_db
def test_index(include):
    """
    Test documentation scripts.

    This test executes the first snippet of code to deploy a smart contract and
    then the second one which indexes it.

    Because we index the blockchain backwards (from most recent to oldest
    block), we want to cover two cases:

    - when the indexer first finds a call, and then the contract,
    - when a new call is indexed after the contract has been indexed.

    In the first case, it will follow this path:

    - TezosProvider.index()
    - TezosProvider.index_call()
    - TezosProvider.index_contract()
    - djwebdapp_tezos.models.contract_indexed_call_args()

    In the second case:

    - TezosProvider.index()
    - TezosProvider.index_call()
    - djwebdapp_tezos.models.call_indexed_call_args()
    """
    variables = {}
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
