import json
import os
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
opg = client.origination(dict(code=source, storage=storage)).send(min_confirmations=1)
res = OperationResult.from_operation_group(opg.opg_result)
address = res[0].originated_contracts[0]
client.contract(address).mint('tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx', 1000).send(min_confirmations=2)
print(f'CONTRACT ADDRESS: {address}')
