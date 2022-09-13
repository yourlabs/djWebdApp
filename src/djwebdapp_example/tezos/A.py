from dataclasses import dataclass
from pymich.michelson_types import Address, BaseContract, Contract, Mutez, Tezos, String


#   A<--|
#  / \  |
# B   C--
# |
# D


@dataclass(kw_only=True)
class A(BaseContract):
    B: Address
    C: Address
    value: String

    def call_B_and_C(self, value_b: String, value_c: String):
        enter_b_entrypoint = Contract[String](self.B, "%set_value_B")
        enter_c_entrypoint = Contract[String](self.C, "%set_value_C")
        self.ops = self.ops.push(
            enter_b_entrypoint,
            Tezos.amount,
            value_b,
        )
        self.ops = self.ops.push(
            enter_c_entrypoint,
            Mutez(0),
            value_c,
        )

    def set_value_B(self, value_b: String):
        enter_b_entrypoint = Contract[String](self.B, "%set_value")
        self.ops = self.ops.push(
            enter_b_entrypoint,
            Tezos.amount,
            value_b,
        )

    def set_value_C(self, value_c: String):
        enter_c_entrypoint = Contract[String](self.C, "%set_value")
        self.ops = self.ops.push(
            enter_c_entrypoint,
            Tezos.amount,
            value_c,
        )

    def set_value(self, value: String):
        self.value = value

    def set_B(self, B: Address):
        self.B = B

    def set_C(self, C: Address):
        self.C = C
