import pytest

from djwebdapp_tezos.models import TezosTransaction

import functools
from pathlib import Path
import os

from pymich.compiler import Compiler
from pytezos import ContractInterface
from pytezos.contract.result import OperationResult


class ContractLoader:
    """
    This object provides a Python API over example contracts, for testing.
    """

    def __init__(self, contract_path):
        self.contract_path = contract_path

    @functools.cached_property
    def source(self):
        with open(self.contract_path) as f:
            return f.read()

    @functools.cached_property
    def compiler(self):
        return Compiler(self.source)

    @functools.cached_property
    def micheline(self):
        return self.compiler.compile_contract()

    @functools.cached_property
    def interface(self):
        return ContractInterface.from_micheline(self.micheline)

    @property
    def dummy(self):
        return self.interface.storage.dummy()

    @property
    def storage(self):
        """ Lazy mutable storage, dummy by default. """
        if '_storage' not in self.__dict__:
            self._storage = self.dummy
        return self._storage

    @storage.setter
    def storage(self, value):
        self._storage = value

    @classmethod
    def factory(cls, path):
        pymich = Path(os.path.dirname(__file__)) / '..'
        paths = [
            Path(path),
            pymich / 'tests' / path,
            pymich / 'tests' / 'end_to_end' / path,
        ]
        for path in paths:
            if path.exists():
                return cls(path.absolute())

    def deploy(self, client, using):
        contract_ci= self.interface.using(**using)
        opg = contract_ci.originate(initial_storage=self.storage).send(min_confirmations=1)
        callee_addr = OperationResult.from_operation_group(opg.opg_result)[
            0
        ].originated_contracts[0]
        return client.contract(callee_addr)


@pytest.mark.django_db
def test_internal(client, blockchain, using):
    loader = ContractLoader('src/djwebdapp_example/tezos/A.py')
    loader.storage['B'] = client.key.public_key_hash()
    loader.storage['C'] = loader.storage['B']
    A = loader.deploy(client, using)
    caller = TezosTransaction.objects.create(
        blockchain=blockchain,
        address=A.address,
    )
    B = loader.deploy(client, using)
    C = loader.deploy(client, using)
    D = loader.deploy(client, using)
    opg1 = A.set_B(B.address).send(min_confirmations=1)
    opg2 = A.set_C(C.address).send(min_confirmations=1)
    # the following 2 should not be indexed
    opg3 = B.set_B(D.address).send(min_confirmations=1)
    opg4 = C.set_C(A.address).send(min_confirmations=1)
    caller.blockchain.provider.index()
    opg5 = A.call_B_and_C(dict(
        value_b='B',
        value_c='C',
    )).send(min_confirmations=1)
    caller.blockchain.wait_blocks()
    caller.blockchain.provider.index()
    result = TezosTransaction.objects.values_list(
        'function', 'args', 'index', 'address',
    ).order_by(
        'level', 'counter', 'nonce'
    )
    expected = [
        (None, None, False, C.address),
        (None, None, False, B.address),
        (None, None, False, D.address),
        (None, None, True, A.address),
        ('set_B', B.address, True, None),
        ('set_C', C.address, True, None),
        ('call_B_and_C', {'value_b': 'B', 'value_c': 'C'}, True, None),
        ('set_value_B', 'B', True, None),
        ('set_value_C', 'C', True, None),
        ('set_value', 'C', True, None),
        ('set_value', 'B', True, None),
    ]
    assert list(result) == expected
