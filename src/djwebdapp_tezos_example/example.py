from dataclasses import dataclass
from pymich.michelson_types import Address, BigMap, Contract, Nat
from pymich.stdlib import SENDER


@dataclass
class FA12(Contract):
    tokens: BigMap[Address, Nat]
    total_supply: Nat
    owner: Address

    def mint(self, _to: Address, value: Nat):
        if SENDER != self.owner:
            raise Exception("Only owner can mint")

        self.total_supply = self.total_supply + value

        self.tokens[_to] = self.tokens.get(_to, Nat(0)) + value

    def getTotalSupply(self) -> Nat:  # noqa
        return self.total_supply
