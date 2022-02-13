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
