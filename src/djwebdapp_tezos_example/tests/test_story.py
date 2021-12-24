import json, os, pytest, time
from pytezos import pytezos
from pytezos.operation.result import OperationResult

from djwebdapp.models import Blockchain, SmartContract
from djwebdapp_tezos_example.models import Balance


def deploy():
    client = pytezos.using(
        key='edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh',
        shell='http://tzlocal:8732',
    )
    path = os.path.join(
         os.path.dirname(__file__),
         '..',
         'example.json',
     )
    source = json.load(open(path))
    storage = {'prim': 'Pair', 'args': [[], {'int': '0'}, {'string':
        'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx'}]}
    operation = client.origination(dict(code=source,
        storage=storage)).autofill().sign().inject(_async=False)
    time.sleep(2)  # wait for sandbox to bake
    opg = client.shell.blocks[operation['branch']:].find_operation(operation['hash'])
    res = OperationResult.from_operation_group(opg)
    address = res[0].originated_contracts[0]
    client.contract(address).mint('tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
            1000).send().autofill().sign().inject()
    return address


@pytest.mark.django_db
def test_sync():
    address = deploy()

    # First, we need to add a blockchain in the database
    blockchain, _ = Blockchain.objects.get_or_create(
        name='Tezos Local',
        provider_class='djwebdapp_tezos.provider.TezosProvider',
        configuration=dict(
            tzkt='http://api:5000',
        ),
    )

    # Then, insert a smart contract with our address
    contract, _ = SmartContract.objects.get_or_create(
        blockchain=blockchain,
        address=address,
    )

    tries = 100
    while not contract.sync():
        tries -= 1
        time.sleep(.1)
    assert tries, 'Contract did not sync'

    assert contract.call_set.count()
    assert contract.fa12
    assert contract.fa12.mint_set.all()
    assert Balance.objects.first().balance == 1000
