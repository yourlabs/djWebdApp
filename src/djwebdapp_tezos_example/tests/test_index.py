import os
import pytest

from djwebdapp.models import SmartContract


@pytest.mark.django_db
def test_blockchain_sync():
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

    100% Evil code so that test code also serves documentation, don't try this
    at home.
    """
    from djwebdapp_tezos_example.example_origination import client, deploy
    address = deploy()

    path = os.path.join(os.path.dirname(__file__), '..', 'example_index.py')
    with open(path) as f:
        source = f.read()
    exec(source, globals(), locals())

    contract = SmartContract.objects.get(address=address)

    # normalized data also synchronized
    assert contract.fa12
    assert contract.fa12.mint_set.all()

    from djwebdapp_tezos_example.models import Balance
    assert Balance.objects.first().balance == 1000

    # test the second case:
    client.contract(address).mint(
        'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
        10,
    ).send(min_confirmations=2)

    contract.blockchain.provider.index()
    assert contract.call_set.count() == 2

    # also test balance was updated
    assert Balance.objects.first().balance == 1010
