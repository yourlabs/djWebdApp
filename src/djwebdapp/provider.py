import random


class Provider:
    def __init__(self, blockchain):
        self.blockchain = blockchain

    def index(self):
        raise NotImplementedError()


def fakehash(leet):
    return f'0x{leet}5EF2D798D17e2ecB37' + str(random.randint(
        1000000000000000, 9999999999999999
    ))


class Success(Provider):
    pass
