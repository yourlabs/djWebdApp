import json, os, pytest, time
from pytezos import pytezos
from pytezos.operation.result import OperationResult

from djwebdapp.models import Blockchain, SmartContract
from djwebdapp_tezos_example.models import Balance


@pytest.mark.django_db
def test_sync():
    """
    Test documentation scripts.

    This test executes the first snippet of code to deploy a smart contract and
    then the second one which indexes it.

    100% Evil code, don't try this at home.
    """
    from djwebdapp_tezos_example.example_origination import address
    path = os.path.join(os.path.dirname(__file__), '..', 'example_index.py')
    with open(path) as f:
        source = f.read()
    exec(source, globals(), locals())
