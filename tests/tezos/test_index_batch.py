import pytest

from djwebdapp.models import Account
from djwebdapp_tezos.models import TezosTransaction

@pytest.mark.django_db
@pytest.mark.parametrize('method', ('index', 'download'))
def test_index_batch_transaction(include, method, blockchain):
    variables = include(
        'djwebdapp_example/tezos',
        'client', 'load', 'deploy', 'blockchain', 'index', 'normalize',
    )
    contract = variables['contract']

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
    result = variables['client'].bulk(mint1, mint2, transfer).send(min_confirmations=2)
    blockchain.wait_blocks()

    if method == 'index':
        contract.blockchain.provider.index()

    elif method == 'download':
        blockchain.configuration['tzkt_url'] = 'http://tzkt-api:5000'
        blockchain.save()
        contract.blockchain.provider.download(contract.address)

    indexed = contract.call_set.filter(hash=result.hash()).order_by('counter')
    # check that we indexed the 3 calls on that hash
    assert indexed.count() == 3

    # check that we have 3 distinct counters
    counters = {cnt for cnt in indexed.values_list('counter', flat=True)}
    assert len(counters) == 3

    # check that args were indexed in appropriate counter order
    assert [*indexed.values_list('args', flat=True)] == [
        {
            '_to': 'tz1Yigc57GHQixFwDEVzj5N1znSCU3aq15td',
            'value': 11,
        },
        {
            '_to': 'tz1Yigc57GHQixFwDEVzj5N1znSCU3aq15td',
            'value': 22
        },
        {
            '_from': 'tz1Yigc57GHQixFwDEVzj5N1znSCU3aq15td',
            '_to': 'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
            'value': 1,
        },
    ]
