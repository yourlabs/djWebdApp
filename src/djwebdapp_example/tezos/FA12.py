from dataclasses import dataclass
from pymich.michelson_types import Account, BigMap, Contract, Nat
from pymich.stdlib import SENDER


@dataclass
class FA12(Contract):
    tokens: BigMap[Account, Nat]
    total_supply: Nat
    owner: Account

    def mint(self, _to: Account, value: Nat):
        if SENDER != self.owner:
            raise Exception("Only owner can mint")

        self.total_supply = self.total_supply + value

        self.tokens[_to] = self.tokens.get(_to, Nat(0)) + value

    def getTotalSupply(self) -> Nat:  # noqa
        return self.total_supply
