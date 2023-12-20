from multiprocessing import get_context
import logging
import random

from django import db
from django.db.models import Q

from djwebdapp.models import Event, Transaction


def call_deploy(arg):
    """
    Wrap a call in a try/except with logging.

    :param arg: Tuple of (logger, call)
    """
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
    """
    Given a QS of calls, return a list of calls with distinct senders.

    :param calls_query_set: Queryset of Calls
    :param n_calls: Number of calls to return
    """
    senders = set()
    distinct_calls = []
    for call in calls_query_set:
        if call.sender not in senders and len(distinct_calls) < n_calls:
            distinct_calls.append(call)
            senders.add(call.sender)

    return distinct_calls


class Provider:
    """
    Base Provider class, encapsulates business logic with blockchains.

    Instanciating a Provider requires either a `blockchain` or a `wallet`
    argument.

    .. warning:: Do not use this class directly, it is meant to be sub-classed
                 for each blockchain type.

    :param blockchain: :py:class:`~djwebdapp.models.Blockchain` object to
                       instanciate the Provider with, in which case the Python
                       client for the blockchain will use its default account.

    :param wallet: :py:class:`~djwebdapp.models.Account` object to bind the
                    provider with, in which case the
                    :py:attr:`~djwebdapp.models.Account.secret_key` must be set
                    in the Account.

    .. note:: You don't need to pass both `wallet` and `blockchain` arguments,
              the provider will instanciate with the `blockchain` attribute of
              the `wallet` argument if any.

    .. py:attribute:: blockchain

        :py:class:`~djwebdapp.models.Blockchain` this provider was instanciated
        for.

    .. py:attribute:: wallet

        :py:class:`~djwebdapp.models.Account` this provider was instanciated
        for, if any.

        .. danger:: When instanciating a provider with a :py:attr:`wallet`,
                    make sure the :py:class:`~djwebdapp.models.Account` has a
                    secret key! Otherwise, the blockchain client will not be
                    able to send any transaction!

    .. py:attribute:: transaction_class

        :py:class:`~djwebdapp.models.Transaction` subclass this provider works
        with. For example, :py:class:`~djwebdapp_tezos.models.TezosTransaction`
        if it's a tezos provider, or a
        :py:class:`~djwebdapp_ethereum.models.EthereumTransaction` if it's an
        ethereum provider. This is supposed to be set as a class attribute by
        the provider subclass.

    .. py:attribute:: exclude_states

        States to exclude when searching for transactions to deploy.
    """
    exclude_states = (
        'held', 'aborted', 'import', 'importing', 'confirm', 'done'
    )

    def __init__(self, blockchain=None, wallet=None):
        self.wallet = wallet
        self.blockchain = wallet.blockchain if wallet else blockchain

    def generate_secret_key(self):
        """
        Generate a secret key.

        Raises NotImplemented in base Provider class.
        """
        raise NotImplementedError()

    @property
    def head(self):
        """
        Return the current block number.

        Raises NotImplemented in base Provider class.
        """
        raise NotImplementedError()

    def download(self, target: str):
        """
        Download a contract history from the configured indexer.

        This will use an indexer such as etherscan or tzkt to download the
        history from a web-API rather than by indexing the blockchain which
        could take a really long while for large contracts.

        :param target: String address of the contract to download history for.
        """
        raise NotImplementedError()

    def index_level(self, level: int):
        """
        Index a given block level.

        Left to implement in new provider subclasses.
        """
        raise NotImplementedError()

    def get_client(self, wallet=None):
        """
        Return the Python client that provider encapsulates.

        :param wallet: :py:class:`~djwebdapp.models.Account` object to use,
                        note that it *must* have a
                        :py:attr:`~djwebdapp.models.Account.secret_key`.
        """
        raise NotImplementedError()

    @property
    def client(self):
        """
        Cached result of :py:meth:`get_client()`
        """
        cached = getattr(self, '_client', None)
        if cached:
            return cached
        self._client = self.get_client()
        return self._client

    @client.setter
    def client(self, value):
        self._client = value

    def index_init(self):
        """
        Query the database for transactions hashes and contract addresses to
        index in :py:meth:`index()`

        Provisions
        """
        self.hashes = list(self.transaction_class.objects.filter(
            blockchain=self.blockchain
        ).filter(
            Q(state='confirm') | ~Q(hash=None)
        ).exclude(
            state='done'
        ).values_list('hash', 'level'))

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

    def check_hash(self, hash_to_check):
        """
        Returns True if hash is in self.hashes
        """
        return any(hash_to_check == hash for hash, _ in self.hashes)

    def deploy(self, transaction):
        """
        Deploy a given :py:class:`~djwebdapp.models.Transaction` object.
        """
        raise NotImplementedError()

    def reorg(self):
        """
        Handle reorg if necessary.

        Compare the head level with the last indexed level, if it's superior
        then consider a reorg happened on the blockchain.

        In this case, empty the level, hash, and address of every
        :py:class:`~djwebdapp.models.Transaction` in DB which has a level
        greater than or equal to the current head level, and set their state to
        `deleted`.
        """
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
        """
        Index the blockchain.

        Return if :py:meth:`reorg()` returns True.

        Iterate over each level from the last indexed level in the
        :py:attr:`djwebdapp.models.Blockchain.index_level` column (or 0) up to
        the current head level. Call :py:meth:`index_level()` for each level.
        """
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

    def spool_contracts(self):
        """
        Return the contracts to deploy, used by :py:meth:`~spool()`.

        Return a QuerySet of :py:attr:`transaction_class` objects of this
        :py:attr:`blockchain` which:

        - are of :py:attr:`~djwebdapp.models.Transaction.kind` ``contract``
        - have no :py:attr:`~djwebdapp.models.Transaction.hash`
        - have code according to
          :py:attr:`~djwebdapp.models.Transaction.has_code`, so that we can
          actually deploy it
        - have no :py:attr:`~djwebdapp.models.Transaction.address`
        - which :py:attr:`~djwebdapp.models.Transaction.state` is not in
          :py:attr:`exclude_states`,
        - which sender :py:class:`~djwebdapp.models.Account` have not deployed
          to the blockchain during this level according to :py:attr:`head` and
          :py:attr:`djwebdapp.models.Account.last_level`
        - which sender has balance above 0
        - ordered by :py:attr:`~djwebdapp.models.Transaction.created_at`
          ascending order, so that it gets the oldest first.
        """
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
        ).select_subclasses()

    def spool_calls(self):
        """
        Return the calls to deploy in :py:meth:`~spool()`.

        Return a QuerySet of :py:attr:`transaction_class` objects of this
        :py:attr:`blockchain` which:

        - are of :py:attr:`~djwebdapp.models.Transaction.kind` ``function``
        - have no :py:attr:`~djwebdapp.models.Transaction.hash`
        - are related to a contract which does have an
          :py:attr:`~djwebdapp.models.Transaction.address`
        - which :py:attr:`~djwebdapp.models.Transaction.state` is not in
          :py:attr:`exclude_states`,
        - which sender :py:class:`~djwebdapp.models.Account` have not deployed
          to the blockchain during this level according to :py:attr:`~head` and
          :py:attr:`djwebdapp.models.Account.last_level`
        - which sender has balance above 0
        - ordered by :py:attr:`~djwebdapp.models.Transaction.created_at`
          ascending order, so that it gets the oldest first.
        """
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
        ).select_subclasses()

    def spool_transfers(self):
        """
        Return the transfers to deploy, used by :py:meth:`~spool()`.

        Return a QuerySet of :py:attr:`transaction_class` objects of this
        :py:attr:`blockchain` which:

        - are of :py:attr:`~djwebdapp.models.Transaction.kind` ``transfer``
        - have no :py:attr:`~djwebdapp.models.Transaction.hash`
        - which :py:attr:`~djwebdapp.models.Transaction.state` is not in
          :py:attr:`exclude_states`,
        - which sender :py:class:`~djwebdapp.models.Account` have not deployed
          to the blockchain during this level according to :py:attr:`head` and
          :py:attr:`djwebdapp.models.Account.last_level`
        - which sender has balance above 0
        - ordered by :py:attr:`~djwebdapp.models.Transaction.created_at`
          ascending order, so that it gets the oldest first.
        """
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

    def spool(self):
        """
        Deploy the next transaction of any kind and return it.

        It checks for the next transaction with the following logic:

        - :py:meth:`~spool_transfers()`: is there any new transfer to deploy?
        - :py:meth:`~spool_contracts()`: is there any *new* contract to deploy
          from an account with balance?
        """
        # senders which have already deployed during this block must be
        # excluded
        # is there any new transfer to deploy from an account with balance?
        transfer = self.spool_transfers().filter(last_fail=None).first()
        if transfer:
            self.logger.info(f'Deploying transfer {transfer}')
            return transfer.deploy()
        self.logger.info('Found 0 transfers to deploy')

        # is there any new contract to deploy from an account with balance?
        contract = self.spool_contracts().filter(last_fail=None).first()

        if contract:
            dependency = contract.dependency_get()
            if dependency:
                contract = dependency
            self.logger.info(f'Deploying contract {contract}')
            contract.deploy()
            return contract
        self.logger.info('Found 0 contracts to deploy')

        n_calls = 15
        calls = self.spool_calls().filter(last_fail=None)
        distinct_calls = get_calls_distinct_sender(calls, n_calls)

        if distinct_calls:
            db.connections.close_all()
            pool = get_context("fork").Pool(n_calls)
            results = pool.map(
                call_deploy,
                [(self.logger, call) for call in list(distinct_calls)]
            )
            for result in results:
                result.save()

            if len(distinct_calls) == 1:
                return distinct_calls[0]
            else:
                return distinct_calls
        self.logger.info('Found 0 calls to send')

        # is there any transfer to retry from an account with balance?
        transfer = self.spool_transfers().order_by('last_fail').first()
        if transfer:
            self.logger.info(f'Retrying transfer {transfer}')
            transfer.deploy()
            return transfer
        self.logger.info('Found 0 transfer to retry')

        # any contract to retry?
        contract = self.spool_contracts().order_by('last_fail').first()
        if contract:
            self.logger.info(f'Retrying contract {contract}')
            contract.deploy()
            return contract
        self.logger.info('Found 0 contract to retry')

        # any call to retry?
        call = self.spool_calls().order_by('last_fail').first()
        if call:
            self.logger.info(f'Retrying function {call}')
            call.deploy()
            return call
        self.logger.info('Found 0 call to retry')

    def normalize(self):
        """
        Run `normalize()` on all un-normalized transactions.

        Call
        :py:meth:`~djwebdapp.models.Transaction.normalize()`
        on each transaction that has not been normalized.

        Internal transactions are normalized after their caller is normalized.
        """
        def normalize_internal(transaction):
            if not transaction.normalized:
                return

            internal_calls_qs = transaction._internal_calls.order_by("nonce")
            for internal in internal_calls_qs.all():
                internal.normalize()

        def normalize_event(event):
            if event.normalized:
                return

            event.normalize()

        transactions = self.transaction_class.objects.filter(
            normalized=False,
            caller=None,
            state='done',
        ).order_by(
            'created_at',
        )

        for transaction in transactions:
            transaction.normalize()
            normalize_internal(transaction)
            for event in transaction.transactionevent_set.all():
                event_subclass = Event.objects.get_subclass(pk=event.pk)
                normalize_event(event_subclass)

    def get_balance(self, address=None):
        """
        Query the blockchain and return the balance of an address.

        .. py:attribute:: address

            Address to get the balance of, use the current client address by
            default.
        """
        raise NotImplementedError()


def fakehash(leet):
    return f'0x{leet}5EF2D798D17e2ecB37' + str(random.randint(
        1000000000000000, 9999999999999999
    ))


class Success(Provider):
    logger = logging.getLogger('djwebdapp_test')

    def get_balance(self, address=None):
        return 1_000_000
