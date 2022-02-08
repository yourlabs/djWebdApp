import functools
import random

from djwebdapp.models import Transaction


class Provider:
    def __init__(self, blockchain):
        self.blockchain = blockchain

    def index_level(self, level):
        raise NotImplementedError()

    def get_client(self, wallet=None):
        raise NotImplementedError()

    @functools.cached_property
    def client(self):
        return self.get_client()

    def index_init(self):
        self.hashes = self.transaction_class.objects.filter(
            blockchain=self.blockchain
        ).exclude(
            hash=None
        ).values_list('hash', flat=True)

        self.contracts = self.transaction_class.objects.exclude(
            address=None,
        ).filter(
            blockchain=self.blockchain,
        )

        self.addresses = self.contracts.values_list(
            'address',
            flat=True,
        )

    def index(self):
        start_level = current_level = self.head

        reorg = (
            self.blockchain.max_level
            and start_level < self.blockchain.max_level
        )
        if reorg:
            # reorg
            Transaction.objects.filter(
                sender__blockchain=self.blockchain,
                level__gte=self.blockchain.max_level,
            ).exclude(level=None).update(
                level=None,
                hash=None,
                address=None,
                state='deleted',
            )
            self.blockchain.max_level = self.blockchain.max_level
            self.blockchain.save()
            return  # commit to reorg in a transaction

        fresh = (
            self.blockchain.max_level
            and start_level == self.blockchain.max_level
        )
        if fresh:
            # no need to go all way back further if we are up to date just
            # check the head
            max_depth = 1

        resume = (
            self.blockchain.max_level
            and start_level > self.blockchain.max_level
        )
        if resume:
            # go all way back to where we left
            max_depth = (start_level - self.blockchain.max_level) or 1

        if not self.blockchain.max_level:
            # go with an arbitrary backlog
            max_depth = 500

        self.index_init()

        while current_level and start_level - current_level < max_depth:
            self.logger.debug(f'Indexing level {current_level}')
            self.index_level(current_level)
            current_level -= 1

        # consider head as suceptible to change
        self.blockchain.max_level = start_level - 1
        self.blockchain.save()


def fakehash(leet):
    return f'0x{leet}5EF2D798D17e2ecB37' + str(random.randint(
        1000000000000000, 9999999999999999
    ))


class Success(Provider):
    pass
