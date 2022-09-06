from dataclasses import dataclass
from pymich.michelson_types import Address, BaseContract, Contract, Mutez, Nat

@dataclass(kw_only=True)
class Proxy(BaseContract):
    callee: Address
    admin: Address
    counter: Nat

    def set_counter(self, new_counter: Nat, price: Mutez):
        increment_counter_entrypoint = Contract[Nat](self.callee, "%set_counter")
        self.ops = self.ops.push(
            increment_counter_entrypoint,
            price,
            new_counter,
        )

    def set_counter_callback(self, new_counter: Nat):
        self.counter = new_counter

    def getCallee(self) -> Address:
        return self.callee
