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

    def transfer(self, _from: Address, _to: Address, value: Nat):
        from_balance = self.tokens.get(_from, Nat(0))

        if (from_balance - value) < Int(0):
            raise Exception("NotEnoughBalance")

        self.tokens[_from] = abs(from_balance - value)

        to_balance = self.tokens.get(_to, Nat(0))

        self.tokens[_to] = to_balance + value

    def getTotalSupply(self) -> Nat:  # noqa
        return self.total_supply
