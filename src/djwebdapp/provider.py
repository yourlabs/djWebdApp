import logging
from multiprocessing import get_context
import random

from django import db
from django.db.models import Q

from djwebdapp.exceptions import (
    AbortedDependencyError,
    CallWithoutContractError,
    ExcludedContractError,
    ExcludedDependencyError,
)
from djwebdapp.models import Transaction
from djwebdapp.signals import get_args


def call_deploy(arg):
    logger, call = arg

    logger.debug(f'starting {call} ...')
    try:
        call.deploy()
    except Exception:
        logger.exception(f'failed {call}')
    else:
        logger.info(f'success {call}')

    return call


def get_calls_distinct_sender(calls_query_set, n_calls):
    senders = set()
    distinct_calls = []
    for call in calls_query_set:
        if call.sender not in senders and len(distinct_calls) < n_calls:
            distinct_calls.append(call)
            senders.add(call.sender)

    return distinct_calls


class Provider:
    exclude_states = (
        'held', 'aborted', 'import', 'importing', 'watching', 'done'
    )
    spool_states = (
        'deleted',
        'deploy',
        'retrying',
    )

    def __init__(self, blockchain=None, wallet=None):
        self.wallet = wallet
        self.blockchain = wallet.blockchain if wallet else blockchain

    def download(self, target):
        """ Download a contract history from the configured indexer. """
        raise NotImplementedError()

    def index_level(self, level):
        raise NotImplementedError()

    def get_client(self, wallet=None):
        raise NotImplementedError()

    def get_args(self, transaction):
        results = get_args.send(
            sender=type(self),
            transaction=transaction,
        )
        for callback, result in results:
            if result:
                return result
        return transaction.args

    @property
    def client(self):
        cached = getattr(self, '_client', None)
        if cached:
            return cached
        self._client = self.get_client()
        return self._client

    @client.setter
    def client(self, value):
        self._client = value

    def index_init(self):
        self.hashes = self.transaction_class.objects.filter(
            blockchain=self.blockchain
        ).filter(
            Q(state='confirm') | ~Q(hash=None)
        ).values_list('hash', flat=True)
        self.logger.info(f'Found {len(self.hashes)} transactions to index')

        self.contracts = self.transaction_class.objects.filter(
            blockchain=self.blockchain,
            index=True,
            kind='contract',
        ).filter(
            Q(state='confirm') | ~Q(address=None),
        )
        print(f'Found {len(self.contracts)} contracts to index')

        self.addresses = self.contracts.values_list(
            'address',
            flat=True,
        )
        self.logger.info(f'Found {len(self.addresses)} addresses to index')

    def deploy(self, transaction):
        raise NotImplementedError()

    def reorg(self):
        current_level = self.head
        reorg = (
            self.blockchain.index_level
            and current_level < self.blockchain.index_level
        )
        if reorg:
            self.logger.warning(
                f'Detected reorg in {self.blockchain} '
                f'from {self.blockchain.index_level} to {current_level}'
            )
            # reorg
            Transaction.objects.filter(
                sender__blockchain=self.blockchain,
                level__gte=current_level,
            ).exclude(level=None).update(
                level=None,
                hash=None,
                address=None,
                state='deleted',
            )
            self.blockchain.index_level = current_level
            self.blockchain.save()
            return True  # commit to reorg in a transaction

    def index(self):
        if self.reorg():
            return  # commit to reorg in a transaction

        self.index_init()

        from django.db.models import Min
        level = self.blockchain.transaction_set.filter(
            state='confirm'
        ).aggregate(
            Min('level')
        )['level__min']
        if not level:
            if self.blockchain.index_level:
                level = self.blockchain.index_level
            else:
                level = self.blockchain.index_level = 0

        while level <= self.head:
            self.logger.info(f'Indexing level {level}')
            self.index_level(level)
            self.blockchain.index_level = level
            level += 1
        self.blockchain.save()

    def transactions(self):
        return self.transaction_class.objects.filter(
            blockchain=self.blockchain,
            hash=None,
            sender__blockchain__is_active=True,
        ).filter(
            Q(sender__last_level__lt=self.head)
            | Q(sender__last_level=None)
        ).exclude(
            Q(sender__balance=None)
            | Q(sender__balance=0)
            | Q(state__in=self.exclude_states)
        ).select_related(
            'blockchain'
        ).order_by(
            'created_at'
        )

    def contracts(self):
        return self.transaction_class.objects.filter(
            blockchain=self.blockchain,
            kind='contract',
            hash=None,
            sender__blockchain__is_active=True,
            has_code=True,
        ).filter(
            Q(address='')
            | Q(address=None)
        ).filter(
            Q(sender__last_level__lt=self.head)
            | Q(sender__last_level=None)
        ).exclude(
            Q(sender__balance=None)
            | Q(sender__balance=0)
            | Q(state__in=self.exclude_states)
        ).select_related(
            'blockchain'
        ).order_by(
            'created_at'
        )

    def calls(self):
        return self.transaction_class.objects.filter(
            blockchain=self.blockchain,
            kind='function',
            hash=None,
            sender__blockchain__is_active=True,
        ).filter(
            Q(sender__last_level__lt=self.head)
            | Q(sender__last_level__isnull=True)
        ).exclude(
            Q(sender__balance=None)
            | Q(sender__balance=0)
            | Q(state__in=self.exclude_states)
            | Q(contract__address='')
            | Q(contract__address__isnull=True)
        ).select_related(
            'blockchain'
        ).order_by(
            'created_at'
        )

    def transfers(self):
        return self.transaction_class.objects.filter(
            blockchain=self.blockchain,
            kind='transfer',
            hash=None,
            sender__blockchain__is_active=True,
            sender__last_level__lt=self.head,
        ).exclude(
            Q(sender__balance=None)
            | Q(sender__balance=0)
            | Q(state__in=self.exclude_states)
        ).select_related(
            'blockchain'
        ).order_by(
            'created_at'
        )

    def get_transaction_dependency(
            self,
            transaction,
            depth=0,
            ascendency=None
    ):
        MAX_DEPTH = 10
        if depth > MAX_DEPTH:
            raise Exception("Transaction max dependency depth exceeded.")

        if not ascendency:
            ascendency = [transaction]

        # return current transaction if no dependencies
        if not transaction.dependencies.count():
            return transaction

        dependencies = transaction.dependencies.select_subclasses(
            self.transaction_class,
        ).all()
        for dependency in dependencies:
            if dependency.state == "done":
                continue
            if dependency.state == "aborted":
                # return the list of transactions that depend on
                # this dependency to that the caller can handle them
                # if it needs to change their states to aborted as
                # well
                raise AbortedDependencyError(dependency, ascendency)
                return [dependency] + ascendency
            if dependency.state == "retry":
                return dependency
            if dependency.state == "deploy":
                try:
                    sub_dependency = self.get_transaction_dependency(
                        dependency,
                        depth + 1,
                        ascendency
                    )
                except AbortedDependencyError as exc:
                    raise AbortedDependencyError(exc.ascendency, [exc.dependency, dependency])

                if dependency.function:
                    if not dependency.contract_id:
                        # dependency is a functionn call without a contract foreign key
                        raise CallWithoutContractError(dependency)
                    if not dependency.contract.address:
                        # dependency is a function call of a contract that isn't yet deployed
                        if dependency.contract.state in exclude_states:
                            raise ExcludedContractError(dependency, exclude_states)
                        return dependency.contract

                if (
                    isinstance(sub_dependency, self.transaction_class)
                    and sub_dependency.state != "done"
                ):
                    # if the sub_dependency is not deployed, return it
                    return sub_dependency
                else:
                    # all sub_dependencies are deployed
                    return dependency
            if dependency.state in self.exclude_states:
                # the dependency is an excluded state that is not
                # `aborted` (caught earlier in the condition), we
                # return nothing so that the caller is aware of the
                # situation
                raise ExcludedDependencyError()
                return None

        # if nothing has returned by this line,then all
        # dependencies are properly deployed, return this transaction as
        # dependency
        return transaction

    def get_candidate_calls(self):
        n_calls = 15
        calls_qs = self.transactions().exclude(level__gte=self.head)
        distinct_candidate_calls = get_calls_distinct_sender(calls_qs, n_calls)
        calls = []
        for candidate_call in distinct_candidate_calls:
            while True:
                try:
                    dependency = self.get_transaction_dependency(candidate_call)
                except AbortedDependencyError as exc:
                    # candidate call has an aborted dependency
                    # mark all dependencies until the aborted dependency
                    # as `aborted`
                    self.transaction_class.objects.filter(
                        pk__in=exc.transactions_pks(),
                    ).update(state="aborted")
                except ExcludedDependencyError:
                    pass
                else:
                    calls.append(dependency)
                    break

                exclude_pks = [
                    tx.pk for tx in distinct_candidate_calls + calls
                ]

                # fetch another candidate call and iterate in the
                # while loop until we find a deployable call
                sender_addresses = set([
                    tx.sender
                    for tx in set(distinct_candidate_calls + calls)
                ])
                sender_addresses.remove(candidate_call.sender)
                candidate_call = self.transactions().exclude(
                    level__gte=self.head,
                    pk__in=exclude_pks,
                    sender__address__in=sender_addresses,
                ).first()
                if not candidate_call:
                    break

        return calls

    def spool(self, bp=False):
        calls = self.get_candidate_calls()

        if calls:
            calls = list(set(calls))
            if calls:
                db.connections.close_all()
                pool = get_context("fork").Pool(len(calls))
                results = pool.map(
                    call_deploy,
                    [(self.logger, call) for call in calls]
                )
                for result in results:
                    result.save()

                if len(calls) == 1:
                    return calls[0]
                else:
                    return calls


def fakehash(leet):
    return f'0x{leet}5EF2D798D17e2ecB37' + str(random.randint(
        1000000000000000, 9999999999999999
    ))


class Success(Provider):
    logger = logging.getLogger('djwebdapp.providers.Success')
