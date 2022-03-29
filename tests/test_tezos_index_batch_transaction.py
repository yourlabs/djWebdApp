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
    # both `mint1` and `mint2` will be included in the same "transaction group",
    # meaning that they will both get the same transaction hash.
    # though `djwebdapp.models.Transaction.hash` have a `UNIQUE` constraint.
    variables['client'].bulk(mint1, mint2).send(min_confirmations=2)

    contract.blockchain.provider.index()

    txs_args = [tx.args for tx in TezosTransaction.objects.filter(function="mint")]
    assert {'_to': 'tz1Yigc57GHQixFwDEVzj5N1znSCU3aq15td', 'value': 22} in txs_args

    # This currently fails. The first transaction in the bulk call will not be
    # indexed
    assert {'_to': 'tz1Yigc57GHQixFwDEVzj5N1znSCU3aq15td', 'value': 11} in txs_args
