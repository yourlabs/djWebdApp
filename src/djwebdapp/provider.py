import random

from .models import Address


class Provider:
    def __init__(self, blockchain):
        self.blockchain = blockchain

    def sync_contract(self, contract):
        raise NotImplementedError()


def fakehash(leet):
    return f'0x{leet}5EF2D798D17e2ecB37' + str(random.randint(
        1000000000000000, 9999999999999999
    ))


class Success(Provider):
    def sync_contract(self, contract):
        contract.gas = 1337
        contract.gas_price = 1337
        contract.address = fakehash('CONTRACT')
        contract.hash = fakehash('TX')
        contract.sender = Address.objects.create(
            address=fakehash('ADDRESS'),
            blockchain=contract.blockchain,
        )
        contract.save()
        contract.call_set.create(
            blockchain=contract.blockchain,
            sender=contract.sender,
            hash=fakehash('CALL'),
        )
