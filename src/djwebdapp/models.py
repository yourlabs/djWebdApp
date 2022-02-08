import importlib
import datetime
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


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


class Address(models.Model):
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
        max_digits=18,
        decimal_places=9,
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
    confirmation_blocks = models.IntegerField(
        default=0,
        help_text='Number of blocks before considering a transaction written',
    )
    configuration = models.JSONField(
        default=dict,
        blank=True,
    )

    def __str__(self):
        return self.name

    @property
    def provider(self):
        parts = self.provider_class.split('.')
        mod = importlib.import_module(
            '.'.join(parts[:-1])
        )
        return getattr(mod, parts[-1])(self)


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
        auto_now_add=True,
        null=True,
        blank=True,
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
    # this is actually defined in each blockchain-specific subclass, left
    # commented here for educationnal purpose
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
        'Address',
        related_name='%(model_name)s_sent',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    receiver = models.ForeignKey(
        'Address',
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
            ('call', 'Call'),
            ('transfer', 'Transfer'),
        )
    )

    def state_set(self, state):
        self.state = state
        self.history.append([
            self.state,
            int(datetime.datetime.now().strftime('%s')),
        ])
        self.save()
        self.blockchain.provider.logger.info(
            f'{self}.state_set({state})'
        )
        # ensure commit happens, is it really necessary ?
        # not sure why not
        # django.db.connection.close()
        # close_old_connections()

    @property
    def provider(self):
        return self.blockchain.provider

    def save(self, *args, **kwargs):
        if not self.kind:
            if not self.function and not self.receiver:
                self.kind = 'contract'
            elif self.function or self.contract:
                self.kind = 'call'
            elif self.amount:
                self.kind = 'transfer'
        return super().save(*args, **kwargs)
