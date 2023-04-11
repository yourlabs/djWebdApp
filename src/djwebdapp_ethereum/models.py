import os

from django.db import models

from djwebdapp.models import Transaction
from djwebdapp.normalizers import Normalizer


class EthereumTransaction(Transaction):
    contract = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='call_set',
        null=True,
        blank=True,
        help_text='Smart contract, appliable to method call',
    )
    caller = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        related_name='_internal_calls',
    )
    abi = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text='Smart contract ABI, if this is a smart contract',
    )
    input = models.TextField(
        blank=True,
        null=True,
        help_text='Input hex string if any',
    )
    bytecode = models.TextField(
        blank=True,
        null=True,
        help_text='Contract bytecode if this is a smart contract to deploy',
    )

    def save(self, *args, **kwargs):
        if self.bytecode:
            self.has_code = True
        return super().save(*args, **kwargs)

    def get_args(self):
        """ Return contract deploy arguments """
        raise NotImplemented()


class EthereumContract(EthereumTransaction):
    """
    Base model class for Ethereum Contracts.

    .. py:attribute:: contract_name

        Name of the contract files, they are expected to be found in the
        ``ethereum`` sub-directory of the application that holds the model that
        is inheriting from this class.

    .. py:attribute:: normalizer_class

        Name of the :py:class:`~djwebdapp.normalizers.Normalizer` subclass to
        call to normalize blockchain transactions for the
        :py:attr:`contract_name` of this model.

    """

    contract_name = None
    normalizer_class = Normalizer

    class Meta:
        proxy = True

    @property
    def contract_path(self):
        if not self.contract_name:
            raise Exception('Please contract_name')

        return os.path.join(
            self._meta.app_config.path,
            'ethereum',
            self.contract_name,
        )

    def save(self, *args, **kwargs):
        if self.contract_name and not self.abi:
            with open(self.contract_path + '.abi', 'r') as f:
                self.abi = f.read()

        if self.contract_name and not self.bytecode:
            with open(self.contract_path + '.bin', 'r') as f:
                self.bytecode = f.read()

        return super().save(*args, **kwargs)

    @property
    def is_internal(self):
        return bool(self.caller_id)

    @property
    def internal_calls(self):
        if self.is_internal:
            txgroup_internal_calls_qs = self.caller._internal_calls
        else:
            txgroup_internal_calls_qs = self._internal_calls

        tx_internal_calls_qs = txgroup_internal_calls_qs.filter(
            nonce__gte=self.nonce if self.nonce else 0,
            sender__address=self.contract.address,
        )
        return tx_internal_calls_qs.order_by('nonce').all()


class EthereumCall(EthereumTransaction):
    """
    Base model class for Ethereum contract function calls.

    .. py:attribute:: entrypoint

        Corresponding function name.
    """
    entrypoint = None

    def save(self, *args, **kwargs):
        if not self.function:
            self.function = self.entrypoint
        if not self.contract:
            self.contract = self.target_contract
        super().save(*args, **kwargs)

    class Meta:
        proxy = True
