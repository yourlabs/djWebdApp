import binascii
import datetime
import importlib
import networkx
import time
import traceback
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q, Max, signals
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from fernet_fields import EncryptedTextField
from model_utils.managers import InheritanceManager

from picklefield.fields import PickledObjectField


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
    An account address on a blockchain.
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
        return self.name or self.address

    @property
    def provider(self):
        return self.blockchain.provider_cls(wallet=self)

    def refresh_balance(self, commit=True):
        new_balance = self.blockchain.provider.get_balance(self.address)
        if new_balance != self.balance:
            self.balance = new_balance
            if commit:
                self.save()
        return self.balance

    def set_secret_key(self, value):
        self.secret_key = binascii.b2a_base64(value).decode()

    def get_secret_key(self):
        return binascii.a2b_base64(self.secret_key)


@receiver(signals.pre_save, sender=Account)
def setup(sender, instance, **kwargs):
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


class Transaction(models.Model):
    """
    Transaction superclass, base for all blockchain-specific classes.

    .. py:attribute:: normalizer_class

        Class of the indexer to use.
    """
    normalizer_class = None
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
        default=True,
        help_text='Check to activate this blockchain',
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
    objects = InheritanceManager()

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
        if state == 'done':
            confirmed_level = self.level + self.blockchain.min_confirmations
            head = self.blockchain.provider.head
            if confirmed_level > head:
                self.blockchain.provider.logger.debug(
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
        return self.blockchain.provider

    def deploy(self):
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
        if not self.kind:
            if not self.function and not self.receiver_id:
                self.kind = 'contract'
            elif self.function:
                self.kind = 'function'
            elif self.amount:
                self.kind = 'transfer'

        if not self.blockchain_id and self.sender_id:
            self.blockchain_id = self.sender.blockchain_id

        return super().save(*args, **kwargs)

    def get_args(self):
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
        """
        graph = self.dependency_graph() or self
        dependency, _ = Dependency.objects.get_or_create(
            dependency=transaction,
            dependent=self,
            graph=graph,
        )
        return dependency

    def dependency_get(self):
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


@receiver(signals.post_save)
def dependency_graph(sender, instance, **kwargs):
    if isinstance(instance, Transaction):
        # contract_id are defined in blockchain specific subclasses
        # getattr here prevents AttributeError: 'Transaction' object has no
        # attribute 'contract_id'
        if instance.function and getattr(instance, 'contract_id', None):
            instance.dependency_add(instance.contract)


class Dependency(models.Model):
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
