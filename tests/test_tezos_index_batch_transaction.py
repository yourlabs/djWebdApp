import pytest

from djwebdapp.models import Account
from djwebdapp_tezos.models import TezosTransaction

@pytest.mark.django_db
def test_index_batch_transaction(include):
    variables = include(
        'djwebdapp_example/tezos',
        'client', 'load', 'deploy', 'blockchain', 'index', 'normalize',
    )

    contract = variables['contract']
    blockchain = variables['blockchain']

    account = Account.objects.create(
        blockchain=blockchain,
        address='tz1Yigc57GHQixFwDEVzj5N1znSCU3aq15td',
    )

    mint1 = variables['client'].contract(variables['address']).mint(
        'tz1Yigc57GHQixFwDEVzj5N1znSCU3aq15td',
        11,
    )
    mint2 = variables['client'].contract(variables['address']).mint(
        'tz1Yigc57GHQixFwDEVzj5N1znSCU3aq15td',
        22,
    )
    transfer = variables['client'].contract(variables['address']).transfer({
        "_from": 'tz1Yigc57GHQixFwDEVzj5N1znSCU3aq15td',
        "_to": 'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
        "value": 1,
    })
    variables['client'].bulk(mint1, mint2, transfer).send(min_confirmations=2)

    contract.blockchain.provider.index()

    mint1_args = TezosTransaction.objects.filter(function="mint", txgroup=0).last().args
    assert {'_to': 'tz1Yigc57GHQixFwDEVzj5N1znSCU3aq15td', 'value': 11} == mint1_args

    mint2_args = TezosTransaction.objects.filter(function="mint", txgroup=1).first().args
    assert {'_to': 'tz1Yigc57GHQixFwDEVzj5N1znSCU3aq15td', 'value': 22} == mint2_args

    tx_transfer_args = TezosTransaction.objects.filter(function="transfer", txgroup=2).first().args
    expected_tx_transfer_args = {
        '_from': 'tz1Yigc57GHQixFwDEVzj5N1znSCU3aq15td',
        '_to': 'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
        'value': 1,
    }
    assert expected_tx_transfer_args == tx_transfer_args
