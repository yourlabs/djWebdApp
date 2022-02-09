# load contract source code
import json
source = json.load(open('src/djwebdapp_example/tezos/FA12.json'))

# initial storage in micheline :P
storage = {
    'prim': 'Pair',
    'args': [
        [],
        {'int': '0'},
        {'string': 'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx'}
    ]}

# originate contract source code with given storage, wait 1 confirmation block
opg = client.origination(
    dict(code=source, storage=storage)
).send(min_confirmations=1)

# get originated contract address
from pytezos.operation.result import OperationResult
res = OperationResult.from_operation_group(opg.opg_result)
address = res[0].originated_contracts[0]

# let's mint some sweet tokens
client.contract(address).mint(
    'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
    1000,
).send(min_confirmations=2)
