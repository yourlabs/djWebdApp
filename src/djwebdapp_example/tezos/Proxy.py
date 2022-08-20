from dataclasses import dataclass
from pymich.michelson_types import Address, BigMap, Contract, Nat
from pymich.stdlib import SENDER


@dataclass
class TransferParam:
    _from: Address
    _to: Address
    value: Nat


@dataclass
class Proxy(Contract):
    fa12: Address
    admin: Address

    def transfer(self, _from: Address, _to: Address, value: Nat):
        param = TransferParam(
            _from=_from,
            _to=_to,
            value=value,
        )
        transaction(Contract(self.fa12), param, TransferParam)
        # ideally, we'd have:
        # self.fa12 typed as FA12 and call:
        # self.fa12.transfer(_from, _to, value)

    def getAdmin(self) -> Address:  # noqa
        return self.admin
