import json, os, time
import djwebdapp_tezos_example
from pytezos import pytezos
from pytezos.operation.result import OperationResult

path = os.path.join(djwebdapp_tezos_example.__path__[0], 'example.json')
source = json.load(open(path))
client = pytezos.using(
    key='edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh',
    shell='http://tzlocal:8732',
)

storage = {'prim': 'Pair', 'args': [[], {'int': '0'}, {'string': 'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx'}]}
operation = client.origination(dict(code=source, storage=storage)).autofill().sign().inject(_async=False)
time.sleep(2)  # wait for sandbox to bake
opg = client.shell.blocks[operation['branch']:].find_operation(operation['hash'])
res = OperationResult.from_operation_group(opg)
address = res[0].originated_contracts[0]
client.contract(address).mint('tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx', 1000).send().autofill().sign().inject()
print(f'CONTRACT ADDRESS: {address}')
