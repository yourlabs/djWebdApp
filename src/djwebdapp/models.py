import binascii
import datetime
import importlib
import networkx
import os
import time
import traceback
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q, Max, signals
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from picklefield.fields import PickledObjectField

from fernet_fields import EncryptedTextField
from model_utils.managers import InheritanceManager


SETTINGS = dict(
    PROVIDERS=(
        ('djwebdapp_tezos.provider.TezosProvider', 'Tezos'),
        ('djwebdapp_ethereum.provider.EthereumProvider', 'Ethereum'),
        ('djwebdapp.provider.Success', 'Test that always succeeds'),
        ('djwebdapp.provider.FailDeploy', 'Test that fails deploy'),
        ('djwebdapp.provider.FailWatch', 'Test that fails watch'),
    )
)
SETTINGS.update(getattr(settings, 'DJBLOCKCHAIN', {}))


class Account(models.Model):
    """
    A blockchain account.

    .. py:attribute:: name

        Optionnal name for this account.

    .. py:attribute:: description

        Optionnal description for this account.

    .. py:attribute:: created_at

        Automatic datetime of the creation of this account in the database.

    .. py:attribute:: updated_at

        Automatic datetime of the last update of this account in the database.

    .. py:attribute:: address

        Account address on the blockchain.

    .. py:attribute:: blockchain

        Foreign key to the :py:class:`~Blockchain` model this account is
        related to.

    .. py:attribute:: balance

        Decimal balance of this account, updated by the
        :py:meth:`~refresh_balance()` method. with the `refresh_balances`
        management command. Uses

    .. py:attribute:: owner

        Foreign key to your User model which owns this account, if any.

    .. py:attribute:: secret_key

        djfernet encrypted private key of this account.

        This is used to sign transactions. The secret key **must** be set with
        the :py:meth:`~set_secret_key()` method.

        A secret key is generated automatically by the
        :py:func:`account_setup()` function *if* the account is not created
        with a :py:attr:`address`.

    .. py:attribute:: counter

        Counter of transactions sent from this account.

    .. py:attribute:: last_level

        Last block level when a transaction was sent from this account.

    .. py:attribute:: index

        Boolean to indicate wether the indexer should index
        all transactions or not.
    """

    name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )
    description = models.TextField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now=True,
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    blockchain = models.ForeignKey(
        'Blockchain',
        on_delete=models.CASCADE,
    )
    balance = models.DecimalField(
        max_digits=80,
        decimal_places=18,
        blank=True,
        editable=False,
        default=0,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    secret_key = EncryptedTextField()
    revealed = models.BooleanField(default=False)
    counter = models.PositiveIntegerField(null=True)
    last_level = models.PositiveIntegerField(null=True)
    index = models.BooleanField(
        default=True,
        help_text='Wether the indexer should index all transactions or not',
    )

    objects = InheritanceManager()

    class Meta:
        unique_together = (
            ('blockchain', 'address'),
        )

    def __str__(self):
        """ Return given name or address or id. """
        return self.name or self.address or self.id

    @property
    def provider(self):
        """
        Return a Provider instance for this wallet.

        The :py:attr:`~Blockchain.provider_cls` returns the class that will be
        used.
        """
        return self.blockchain.provider_cls(wallet=self)

    def refresh_balance(self, commit=True):
        """
        Refresh the balance of this account.

        Using :py:meth:`~djwebdapp.provider.Provider.get_balance()`, it
        will update :py:attr:`~balance` field and save the model.

        Then, return the :py:attr:`~balance`.

        :param commit: Needs to be True for this method to actually save
                       the model.
        """
        new_balance = self.blockchain.provider.get_balance(self.address)
        if new_balance != self.balance:
            self.balance = new_balance
            if commit:
                self.save()
        return self.balance

    def set_secret_key(self, value):
        """
        Set the encrypted secret key.

        :param value: The secret key to set.
        """
        self.secret_key = binascii.b2a_base64(value).decode()

    def get_secret_key(self):
        """
        Returns the account binary secret key.
        """
        return binascii.a2b_base64(self.secret_key)


@receiver(signals.pre_save, sender=Account)
def account_setup(sender, instance, **kwargs):
    """
    Initial account setup, pre_save signal.

    If the :py:class:`Account` is created with a
    :py:attr:`~Account.secret_key` and without any :py:attr:`~Account.address`
    and the :py:attr:`Blockchain.provider` supports it, then it will fetch the
    :py:attr:`~Account.address` automatically.

    If the :py:class:`Account` is created without an
    :py:attr:`~Account.address` nor a :py:attr:`~Account.secret_key` then it is
    considered that you are creating a new wallet and the
    :py:meth:`djwebdapp.provider.Provider.generate_secret_key()` method will
    generate a py:attr:`~Account.secret_key`.

    If the :py:attr:`~Account.balance` is not set at all, then it will be set
    with the :py:meth:`~Account.refresh_balance()` method.
    """
    if instance.secret_key and not instance.address:
        if hasattr(instance.provider, 'get_address'):
            # for providers which support it
            instance.address = instance.provider.get_address()

    elif not instance.address and not instance.secret_key:
        instance.address, secret_key = \
            instance.blockchain.provider.generate_secret_key()
        instance.set_secret_key(secret_key)

    if not instance.balance:
        instance.refresh_balance(commit=False)


class Blockchain(models.Model):
    """
    Class to represent a blockchain.

    .. py:attribute:: name

        Name of the blockchain.

    .. py:attribute:: provider_class

        Provider class to use for this blockchain.

    .. py:attribute:: is_active

        Boolean to indicate wether this blockchain is active or not.

    .. py:attribute:: description

        Optionnal description for this blockchain.

    .. py:attribute:: unit

        Unit name of the blockchain, ie. eth, xtz...

    .. py:attribute:: unit_micro

        Unit name of the smallest unit of the blockchain, ie. wei, mutez...

    .. py:attribute:: index_level

        Highest indexed level.

    .. py:attribute:: min_level

        Lowest indexed level

    .. py:attribute:: min_confirmations

        Number of confirmation blocks from confirm to done states.

    .. py:attribute::configurations

        JSON field to store blockchain specific configurations.

    """
    name = models.CharField(
        max_length=100,
    )
    provider_class = models.CharField(
        max_length=255,
        choices=SETTINGS['PROVIDERS'],
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Check to activate this blockchain',
    )
    description = models.TextField(
        blank=True,
        help_text='Free text to describe the blockchain to users',
    )
    unit = models.CharField(
        max_length=15,
        help_text='Unit name, ie. btc, xtz...',
    )
    unit_micro = models.CharField(
        max_length=15,
        help_text='Unit name, ie. satoshi, mutez...',
    )
    index_level = models.PositiveIntegerField(
        default=None,
        blank=True,
        null=True,
        help_text='Highest indexed level',
    )
    min_level = models.PositiveIntegerField(
        default=None,
        blank=True,
        null=True,
        help_text='Lowest indexed level',
    )
    min_confirmations = models.PositiveIntegerField(
        default=2,
        help_text='Number of confirmation blocks from confirm to done states',
    )
    configuration = models.JSONField(
        default=dict,
        blank=True,
    )

    def __str__(self):
        return self.name

    @property
    def provider_cls(self):
        """ Return the imported provider class. """
        parts = self.provider_class.split('.')
        mod = importlib.import_module('.'.join(parts[:-1]))
        return getattr(mod, parts[-1])

    @property
    def provider(self):
        """ Return a fresh instance of the provider class bound to self. """
        return self.provider_cls(blockchain=self)

    def wait(self):
        """
        Wait for all transactions to be confirmed by min_confirmations blocks.

        For use in between spool and index calls:

        .. code-block:: python

            blockchain.provider.spool()
            blockchain.wait()
            blockchain.provider.index()
        """
        index_level = self.transaction_set.filter(
            state='confirm',
        ).aggregate(
            index_level=Max('level')
        )['index_level']
        if not index_level:
            return  # no transaction to wait.
        self.wait_level(index_level + self.min_confirmations)

    def wait_level(self, level):
        """ Wait for the blockchain head to reach a given level. """
        while self.provider.head < level:
            time.sleep(.1)

    def wait_blocks(self, blocks=None):
        """ Wait for the blockchain head to advance a number of blocks. """
        blocks = blocks or self.min_confirmations
        self.wait_level(self.provider.head + blocks)


class Node(models.Model):
    """
    Blockchain node that we can use to query.

    .. py:attribute:: blockchain

        Foreign key to the :py:class:`~Blockchain` model this node is
        related to.

    .. py:attribute:: name

        Node name, generated from endpoint if empty.

    .. py:attribute:: endpoint

        Node endpoint to query.

    .. py:attribute:: is_active

        Boolean to indicate wether this node is active or not.

    .. py:attribute:: priority

        Nodes with the highest priority will be used first.

    """
    blockchain = models.ForeignKey(
        'Blockchain',
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        max_length=100,
        help_text='Node name, generated from endpoint if empty',
    )
    endpoint = models.URLField(
        help_text='Node endpoint to query',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Check to activate this node',
    )
    priority = models.IntegerField(
        default=0,
        help_text='Nodes with the highest priority will be used first',
    )


class Explorer(models.Model):
    """
    Blockchain explorer we can use to generate external links.

    .. py:attribute:: blockchain

        Foreign key to the :py:class:`~Blockchain` model this explorer is
        related to.

    .. py:attribute:: name

        Explorer name, generated from url template if empty.

    .. py:attribute:: url_template

        URL template to generate the explorer link.

    .. py:attribute:: is_active

        Boolean to indicate wether this explorer is active or not.

    """
    blockchain = models.ForeignKey(
        'Blockchain',
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        max_length=100,
        help_text='Explorer name, generated from url template if empty',
    )
    url_template = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Check to activate this explorer',
    )


class TransactionManager(InheritanceManager):
    """
    Manager for the :py:class:`Transaction` model.

    This Model Manager overrides `get_or_create()` and `update_or_create()` to
    handle parent foreign keys dynamically.
    """
    @property
    def parent_fk_column(self):
        """ Return the name of the foreign key to the parent. """
        return self.model._meta.get_ancestor_link(
            self.model._meta.get_parent_list()[0]
        ).name

    def find_or_create(self, lookup_attributes, defaults=None):
        """ Find or create a transaction model. """
        instance = self.filter(**lookup_attributes).first()
        if not instance:
            instance = self.model(
                **lookup_attributes,
                **(defaults or {}),
            )
            instance.save_base(raw=True, force_insert=True)
            instance.refresh_from_db()
            return instance, True
        return instance, False

    def update_or_create(self, *args, **kwargs):
        """ Same as Django's, with dynamic parent fk handled. """
        if (
            self.parent_fk_column not in kwargs
            and f'{self.parent_fk_column}_id' not in kwargs
        ):
            return super().update_or_create(*args, **kwargs)

        defaults = kwargs["defaults"]
        del kwargs["defaults"]
        lookup_attributes = kwargs

        instance, created = self.find_or_create(lookup_attributes, defaults)
        if created:
            return instance, created

        for key, value in defaults.items():
            setattr(instance, key, value)
        instance.save()
        return instance, False

    def get_or_create(self, *args, **kwargs):
        """ Same as Django's, with dynamic parent fk handled. """
        if self.parent_fk_column not in kwargs:
            return super().get_or_create(*args, **kwargs)

        if instance := self.find_or_create(kwargs):
            return instance

        instance = self.filter(**kwargs).first()
        return instance, False


class Transaction(models.Model):
    """
    Transaction superclass, base for all blockchain-specific classes.

    .. py:attribute:: normalizer_class

        Name of the :py:class:`~djwebdapp.normalizers.Normalizer` subclass to
        call to normalize blockchain transactions for contracts subclassing
        this model.

    .. py:attribute:: id

        UUID primary key.

    .. py:attribute:: created_at

        Datetime when the transaction was created.

    .. py:attribute:: updated_at

        Datetime when the transaction was last updated.

    .. py:attribute:: name

        Optional free label name.

    .. py:attribute:: description

        Optional description text.

    .. py:attribute:: blockchain

        Foreign key to the :py:class:`~Blockchain` model this transaction is
        related to.

    .. py:attribute:: level

        Level of the blockchain when the transaction was send.

    .. py:attribute:: hash

        Transaction hash.

    .. py:attribute:: counter

        Transaction counter. Used to avoid replay attack.
        This counter is filled by the blockchain provider.

    .. py:attribute:: nonce

        Transaction nonce. Used to order transactions in the same block.

    .. py:attribute:: gasprice

        Gas price used to send the transaction.

    .. py:attribute:: gas

        Number of gas used to send the transaction.

    .. py:attribute:: last_fail

        If the transaction failed, this field contains the datetime of the
        last failure.

    .. py:attribute:: max_fails

        Number of failures to retry before aborting transaction.

    .. py:attribute:: has_code

        If the transaction is a contract creation, and the transaction
        contains the deployed contract code, this field is set to True.

    .. py:attribute:: metadata

        This field contains the metadata of the transaction.

    .. py:attribute:: normalized

        Enabled when transaction is normalized.
        Set True by the :py:meth:`~Transaction.normalize` method.

    .. py:attribute:: state

        Status of the transaction. By default, the transaction is in the
        `deploy` state. When the transaction is indexed, the state is set to
        `done`.
        The state is updated by the :py:meth:`~state_set` method.

    .. py:attribute:: error

        If the transaction failed, this field contains the error message.

    .. py:attribute:: history

        History of the state of the transaction associated with the datetime
        of the state change.

    .. py:attribute:: amount

        Amount send by the transaction if there is.

    .. py:attribute:: args

        Arguments, appliable to deployments or method calls.

    .. py:attribute:: address

        Contract address, appliable to method calls.

    .. py:attribute:: function

        Function name, if this is a method call.

    .. py:attribute:: sender

        Sender :py:class:`~Account` that send the transaction.

    .. py:attribute:: receiver

        Receiver :py:class:`~Account` , if this is a transfer.

    .. py:attribute:: kind

        Kind of transaction. Can be `contract`, `function` or `transfer`.

    .. py:attribute:: index

        Boolean to indicate wether the indexer should index all
        transactions or not.

    .. py:attribute:: contract

        Smart contract related to this transaction, appliable to method call
        transactions.

    .. py:attribute:: caller

        Transaction that called this one, if any.

    .. py:attribute:: target_contract

        In your own subclasses for function calls, this should be an FK to the
        contract subclass, then :py:meth:`save()` will provision
        :py:attr:`contract` from the parent model of the target contract.

    .. py:attribute:: entrypoint

        In your own subclasses for function calls, this should be the name of
        the function that corresponds to the subclass, for example,
        FA12TezosMint.entrypoint is set to the `"mint"` string.
        Then, :py:meth:`save()` can provision :py:attr:`function` from that.

    .. py:attribute:: contract_name

        In your own subclasses for contract transactions, this should be the
        name of the file that contains smart contract code, without extension.
        The file must be in the sub-directory `contracts` of the django app of
        the model.
        """
    normalizer_class = None
    entrypoint = None
    target_contract = None
    contract_name = None

    id = models.UUIDField(
        primary_key=True,
        editable=False,
        default=uuid.uuid4
    )
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now=True,
    )
    name = models.CharField(
        help_text='Free label',
        max_length=100,
        null=True,
        blank=True,
    )
    description = models.TextField(
        help_text='Free description text',
        null=True,
        blank=True,
    )
    blockchain = models.ForeignKey(
        'Blockchain',
        on_delete=models.CASCADE,
    )
    level = models.PositiveIntegerField(
        db_index=True,
        null=True,
        blank=True,
    )
    hash = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    counter = models.PositiveIntegerField(
        null=True,
    )
    nonce = models.IntegerField(
        default=-1,
    )
    number = models.IntegerField(
        default=None,
        blank=True,
        null=True,
    )
    gasprice = models.BigIntegerField(
        blank=True,
        null=True,
    )
    gas = models.BigIntegerField(
        blank=True,
        null=True,
    )
    last_fail = models.DateTimeField(
        null=True,
        blank=True,
    )
    max_fails = models.PositiveIntegerField(
        default=10,
        help_text='Number of failures to retry before aborting transaction',
    )
    has_code = models.BooleanField(
        default=False,
        help_text='Checked if this transaction has smart contract code.',
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    STATE_CHOICES = (
        ('held', _('Held')),
        ('deleted', _('Deleted during reorg')),
        ('aborted', _('Aborted')),
        ('deploy', _('To deploy')),
        ('deploying', _('Deploying')),
        ('retry', _('To retry')),
        ('retrying', _('Retrying')),
        ('confirm', _('Deployed to confirm')),
        ('done', _('Confirmed finished')),
    )
    normalized = models.BooleanField(
        default=False,
        help_text='Enabled when transaction is normalized',
    )
    state = models.CharField(
        choices=STATE_CHOICES,
        default='deploy',
        max_length=200,
        db_index=True,
    )
    error = models.TextField(blank=True, null=True)
    history = models.JSONField(default=list)
    states = [i[0] for i in STATE_CHOICES]
    amount = models.DecimalField(
        max_digits=80,
        db_index=True,
        decimal_places=18,
        blank=True,
        default=0,
    )
    args = PickledObjectField(
        default=None,
        null=True,
        blank=True,
        help_text='Arguments, appliable to deployments or method calls',
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text='Contract address, appliable to method calls',
    )
    # This relation is actually in blockchain specific subclasses.
    # contract = models.ForeignKey(
    #     'self',
    #     on_delete=models.CASCADE,
    #     related_name='call_set',
    #     null=True,
    #     blank=True,
    #     help_text='Smart contract, appliable to method call',
    # )
    function = models.CharField(
        max_length=100,
        db_index=True,
        null=True,
        blank=True,
        help_text='Function name, if this is a method call',
    )
    sender = models.ForeignKey(
        'Account',
        related_name='%(model_name)s_sent',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    receiver = models.ForeignKey(
        'Account',
        related_name='%(model_name)s_received',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text='Receiver address, if this is a transfer',
    )
    kind = models.CharField(
        db_index=True,
        blank=True,
        null=True,
        max_length=8,
        choices=(
            ('contract', 'Contract'),
            ('function', 'Function call'),
            ('transfer', 'Transfer'),
        )
    )
    index = models.BooleanField(
        default=True,
        help_text='Wether the indexer should index all transactions or not',
    )
    objects = TransactionManager()

    class Meta:
        unique_together = (
            'blockchain',
            # 'level', ??
            'hash',
            'counter',
            'nonce',
        )
        ordering = ['-created_at']

    def __str__(self):
        if self.name:
            return str(self.name)
        elif self.kind == 'contract' and self.address:
            return self.address
        elif self.hash:
            return str(self.hash)
        elif self.function:
            return f'{self.function}()'
        elif self.amount:
            if getattr(self, 'unit_smallest', None):
                return f'{self.amount}{self.unit_smallest}'
            else:
                return f'{self.amount}'
        else:
            return str(self.pk)

    def state_set(self, state):
        """
        Set :py:attr:`~state` attribute and save it to the :py:attr:`~history`.
        """
        if state == 'done':
            confirmed_level = self.level + self.blockchain.min_confirmations
            head = self.blockchain.provider.head
            if confirmed_level > head:
                self.blockchain.provider.logger.info(
                    f'Set {self} to confirm instead of done'
                )
                state = 'confirm'

        self.state = state
        self.history.append([
            self.state,
            int(datetime.datetime.now().strftime('%s')),
        ])
        self.blockchain.provider.logger.info(
            f'{self}.state={state}'
        )
        self.save()

    @property
    def provider(self):
        """
        Return the blockchain's :py:class:`~djwebdapp.provider.Provider`.
        """
        return self.blockchain.provider

    def deploy(self):
        """
        Deploy the transaction.

        Wrapper around the :py:meth:`djwebdapp.provider.Provider.deploy()`
        method to deploy this trasnsaction.

        In case of exception, it will log the exception, set
        :py:attr:`last_fail`, and count the number of deploy attempts in
        :py:attr:`history`.

        If the deploy attempts count is above the :py:attr:`max_fails` field,
        then set :py:attr:`state` to `aborted`, otherwise, set it to `retry`.
        """
        self.provider.logger.info(f'Deploying {self}')
        self.state_set('deploying')
        try:
            self.sender.provider.deploy(self)
        except Exception:
            self.sender.provider.logger.exception('Deploy fail')
            self.last_fail = timezone.now()

            deploys_since_last_start = 0
            for logentry in reversed(self.history):
                if logentry[0] == 'deploying':
                    deploys_since_last_start += 1
                elif logentry[0] == 'aborted':
                    break

            if deploys_since_last_start >= self.max_fails:
                message = f'Aborting because >= {self.max_fails} failures,'
                self.error = ' '.join([
                    message,
                    'last error:',
                    self.error or '',
                ])
                self.state_set('aborted')
            else:
                self.state_set('retry')
            raise
        else:
            self.last_fail = None
            self.error = ''
            self.state_set('done')
            # indexer is supposed to place it in done

    def save(self, *args, **kwargs):
        """
        Save the transaction in the database.

        Sets :py:attr:`kind` based on the attributes of this transaction and
        :py:attr:`blockchain` from the :py:attr:`sender` automatically.

        Also, provision :py:attr:`~function` and :py:attr:`~contract` from
        :py:attr:`~entrypoint` and :py:attr:`~target_contract`.
        """
        # those would be defined by subclasses
        self_contract = getattr(self, 'contract', None)
        self_target_contract = getattr(self, 'target_contract', None)
        if not self_contract and self_target_contract:
            self.contract = self.target_contract
        if not self.function and self.entrypoint:
            self.function = self.entrypoint

        if not self.kind:
            if not self.function and not self.receiver_id:
                self.kind = 'contract'
            elif self.function:
                self.kind = 'function'
            elif self.amount:
                self.kind = 'transfer'

        if not self.blockchain_id and self.sender_id:
            self.blockchain_id = self.sender.blockchain_id

        if not self.blockchain_id and self.contract_id:
            self.blockchain_id = self.contract.blockchain_id

        return super().save(*args, **kwargs)

    def get_args(self):
        """
        Return the arguments of the transaction.
        """
        return self.args

    def dependency_graph(self):
        """
        Return the dependency graph this transaction is part of, if any.
        """
        dependency = Dependency.objects.filter(
            Q(dependent=self) | Q(dependency=self)
        ).first()
        if dependency:
            return dependency.graph

    def dependency_add(self, transaction):
        """
        Add a transaction that must be deployed before this one.

        :param transaction: The transaction that must be deployed before this
                            one.
        """
        graph = self.dependency_graph() or self
        dependency, _ = Dependency.objects.get_or_create(
            dependency=transaction,
            dependent=self,
            graph=graph,
        )
        return dependency

    def dependency_get(self):
        """
        Return the transaction that must be deployed before this one.
        """
        dependencies = Dependency.objects.filter(
            graph=self.dependency_graph(),
        ).exclude(
            dependent__state='done',
        ).select_related('dependency')
        graph = networkx.DiGraph()
        for dependency in dependencies:
            if dependency.dependency.state == "done":
                graph.add_node(dependency.dependent_id)
            else:
                graph.add_edge(
                    dependency.dependency_id,
                    dependency.dependent_id,
                )

        topological_sort = [node for node in networkx.topological_sort(graph)]
        if len(topological_sort):
            tx_id = topological_sort[0]
            tx = Transaction.objects.filter(
                id=tx_id,
            ).select_subclasses().first()
            return tx

    def normalizer_get(self):
        """
        Return the normalizer class for this transaction.
        """
        if isinstance(self.normalizer_class, str):
            from .normalizers import Normalizer
            return Normalizer._registry[self.normalizer_class]
        elif self.normalizer_class:
            return self.normalizer_class

    def normalize(self):
        """
        Method invoked when normalizing a transaction.

        By default, this relies on
        :py:attr:`~djwebdapp.models.Transaction.normalizer_class`
        """
        contract = self.contract_subclass()
        if not contract:
            return

        normalizer = contract.normalizer_get()
        if not normalizer:
            return

        try:
            normalizer.normalize(self, contract)
        except Exception:
            self.sender.provider.logger.exception('Exception in normalization')
            self.error = traceback.format_exc()
            self.last_fail = timezone.now()
        else:
            self.normalized = True
            self.error = ''
            self.last_fail = None
        self.save()

    @property
    def contract_path(self):
        if not self.contract_name:
            raise Exception('Please contract_name')

        return os.path.join(
            self._meta.app_config.path,
            'contracts',
            self.contract_name,
        )

    def contract_subclass(self):
        """
        Return the subclass of the `.contract` relation.
        """
        if self.kind == 'contract':
            return Transaction.objects.get_subclass(pk=self.pk)

        if not self.contract_id:
            return

        try:
            return Transaction.objects.get_subclass(pk=self.contract_id)
        except Transaction.DoesNotExist:
            pass


class Event(models.Model):
    name = models.CharField(max_length=500)
    args = PickledObjectField(
        default=dict,
        blank=True,
    )
    event_index = models.PositiveBigIntegerField()
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        null=True,
        related_name="transactionevent_set",
    )
    normalized = models.BooleanField(
        default=False,
    )

    objects = InheritanceManager()

    def contract_subclass(self):
        return self.transaction.contract_subclass()

    def normalize(self):
        contract = self.contract_subclass()

        if not contract:
            return

        normalizer = contract.normalizer_get()
        if not normalizer:
            return

        try:
            normalizer.normalize_event(self, contract)
        except Exception:
            contract.provider.logger.exception('Exception in event normalizer')
        else:
            self.normalized = True
            self.save()


@receiver(signals.post_save)
def dependency_graph(sender, instance, **kwargs):
    """
    If the transaction is a contract call, then add the contract as dependency.
    """
    if isinstance(instance, Transaction):
        # contract_id are defined in blockchain specific subclasses
        # getattr here prevents AttributeError: 'Transaction' object has no
        # attribute 'contract_id'
        if instance.function and getattr(instance, 'contract_id', None):
            instance.dependency_add(instance.contract)


class Dependency(models.Model):
    """
    A dependency between two transactions.

    When a transaction is deployed, it is checked if it has a dependency.
    If it does, the transaction is not deployed, but the dependency is
    checked instead. If the dependency is deployed, the transaction
    is deployed. Otherwise, the transaction is not.

    .. py:attribute:: dependent

        The :py:class:`~djwebdapp.models.Transaction` that depends on the
        :py:attr:`~dependency` one.

    .. py:attribute:: dependency

        The :py:class:`~djwebdapp.models.Transaction` that is required to be
        deployed before the :py:attr:`~dependent` one.

    .. py:attribute:: graph

        The :py:class:`~djwebdapp.models.Transaction` that this graph
        was created for. This is used for performance reasons, to not
        have to load the full dependency table for every transaction.

    .. py:attribute:: created_at

        The time the dependency was created.

    .. py:attribute:: updated_at

        The time the dependency was updated.

    """
    dependent = models.ForeignKey(
        'Transaction',
        on_delete=models.CASCADE,
    )
    dependency = models.ForeignKey(
        'Transaction',
        on_delete=models.CASCADE,
        related_name='dependent_set',
    )
    # This serves purely for performance, to not have to load the full
    # dependency table for every transaction.
    graph = models.ForeignKey(
        'Transaction',
        on_delete=models.CASCADE,
        related_name='graph',
        help_text='The transaction this graph was created for',
    )
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now=True,
    )
