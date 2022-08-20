from dataclasses import dataclass
from pymich.michelson_types import Tezos, BaseContract, Nat, Mutez


@dataclass(kw_only=True)
class Callee(BaseContract):
    counter: Nat
    price: Mutez

    def set_counter(self, new_counter: Nat):
        if Tezos.amount != self.price:
            raise Exception("Not the right price")

        self.counter = new_counter

    def get_counter(self) -> Nat:
        return self.counter
