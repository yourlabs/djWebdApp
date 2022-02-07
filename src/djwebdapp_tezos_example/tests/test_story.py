import os
import pytest

from djwebdapp.models import SmartContract


@pytest.mark.django_db
def test_blockchain_sync():
    """
    Test documentation scripts.

    This test executes the first snippet of code to deploy a smart contract and
    then the second one which indexes it.

    100% Evil code so that test code also serves documentation, don't try this
    at home.
    """
    from djwebdapp_tezos_example.example_origination import address

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
