import datetime
import importlib
import time
import uuid

from django.conf import settings
from django.db import models
from django.db.models import signals
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from fernet_fields import EncryptedBinaryField
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
    An account address on a blockchain.

    Note to confuse with :py:class:`djwebdapp_tezos.models.Wallet`.
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
    secret_key = EncryptedBinaryField()
    revealed = models.BooleanField(default=False)
    counter = models.PositiveIntegerField(null=True)
    last_level = models.PositiveIntegerField(null=True)

    objects = InheritanceManager()

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


@receiver(signals.pre_save, sender=Account)
def setup(sender, instance, **kwargs):
    if instance.secret_key and not instance.address:
        if hasattr(instance.provider, 'get_address'):
            # for providers which support it
            instance.address = instance.provider.get_address()

    elif not instance.address and not instance.secret_key:
        instance.address, instance.secret_key = \
            instance.blockchain.provider.generate_secret_key()

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
    max_level = models.PositiveIntegerField(
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
    configuration = models.JSONField(
        default=dict,
        blank=True,
    )

    def __str__(self):
        return self.name

    @property
    def provider_cls(self):
        parts = self.provider_class.split('.')
        mod = importlib.import_module('.'.join(parts[:-1]))
        return getattr(mod, parts[-1])

    @property
    def provider(self):
        return self.provider_cls(blockchain=self)

    def wait(self, level):
        while self.provider.head < level:
            time.sleep(.1)


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
    datetime = models.DateTimeField(
        null=True,
        blank=True,
        auto_now=True,
    )
    hash = models.CharField(
        unique=True,
        max_length=255,
        null=True,
        blank=True,
    )
    gasprice = models.BigIntegerField(
        blank=True,
        null=True,
    )
    gas = models.BigIntegerField(
        blank=True,
        null=True,
    )
    level = models.PositiveIntegerField(
        db_index=True,
        null=True,
        blank=True,
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
        ('retrying', _('Retrying')),
        ('confirm', _('To confirm')),
        ('confirming', _('Confirming')),
        ('done', _('Finished')),
    )
    state = models.CharField(
        choices=STATE_CHOICES,
        default='held',
        max_length=200,
        db_index=True,
    )
    error = models.TextField(blank=True)
    history = models.JSONField(default=list)
    states = [i[0] for i in STATE_CHOICES]
    amount = models.PositiveIntegerField(
        db_index=True,
        null=True,
        blank=True,
    )
    args = models.JSONField(
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
    contract_address = models.CharField(max_length=255, null=True, blank=True)
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
    error = models.TextField(
        null=True,
        blank=True,
    )
    objects = InheritanceManager()

    def __str__(self):
        if self.name:
            return str(self.name)
        elif self.hash:
            return str(self.hash)
        elif self.function:
            return f'{self.name}.{self.function}()'
        elif self.amount:
            return f'{self.amount}xTZ'
        else:
            return str(self.pk)

    def state_set(self, state):
        self.state = state
        self.history.append([
            self.state,
            int(datetime.datetime.now().strftime('%s')),
        ])
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
                self.state_set('retrying')
            raise
        else:
            self.last_fail = None
            self.error = ''
            if self.kind == 'contract':
                self.state_set('watching')
            else:
                self.state_set('done')

    def save(self, *args, **kwargs):
        if not self.kind:
            if not self.function and not self.receiver:
                self.kind = 'contract'
            elif self.function:
                self.kind = 'function'
            elif self.amount:
                self.kind = 'transfer'

        if not self.contract_address and getattr(self, 'contract_id', ''):
            self.contract_address = self.contract.contract_address

        if not self.blockchain_id and self.sender_id:
            self.blockchain_id = self.sender.blockchain_id

        return super().save(*args, **kwargs)
