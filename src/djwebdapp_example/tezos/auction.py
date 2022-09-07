from pymich.michelson_types import *
from pymich.stdlib import transaction


class Auction(BaseContract):
    owner: Address
    top_bidder: Address
    bids: BigMap[Address, Mutez]

    def bid(self) -> None:
        if Tezos.sender in self.bids:
            raise Exception("You have already made a bid")

        self.bids[Tezos.sender] = Tezos.amount
        if Tezos.amount > self.bids[self.top_bidder]:
            self.top_bidder = Tezos.sender

    def collectTopBid(self) -> None:
        if Tezos.sender != self.owner:
            raise Exception("Only the owner can collect the top bid")

        transaction(Contract[Unit](Tezos.sender), self.bids[self.top_bidder], Unit())

    def claim(self) -> None:
        if not (Tezos.sender in self.bids):
            raise Exception("You have not made any bids!")

        if Tezos.sender == self.top_bidder:
            raise Exception("You won!")

        transaction(Contract[Unit](Tezos.sender), self.bids[Tezos.sender], Unit())
