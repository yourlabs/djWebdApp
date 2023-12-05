from django.db import models

from djwebdapp.models import Event, Transaction
from djwebdapp.normalizers import Normalizer


class EthereumTransaction(Transaction):
    """
    Base model for Ethereum transactions.

    .. py:attribute:: abi

        Smart contract ABI code.

    .. py:attribute:: bytecode

        Smart contract bytecode.
    """
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
        """
        Sets :py:attr:`~djwebdapp.models.Transaction.has_code` if
        :py:attr:`bytecode` is set.
        """
        if self.bytecode and self.abi:
            self.has_code = True
        return super().save(*args, **kwargs)

    @property
    def receipt(self):
        return self.provider.client.eth.get_transaction_receipt(self.hash)

    @property
    def contract_ci(self):
        return self.provider.client.eth.contract(
            address=self.contract.address,
            abi=self.contract.abi,
        )

    def get_event(self, event_name):
        event = getattr(
            self.contract_ci.events,
            event_name,
        )()
        return event.process_receipt(self.receipt)


class EthereumContract(EthereumTransaction):
    """
    Base model class for Ethereum Contracts.

    .. py:attribute:: contract_name

        Name of the contract files, they are expected to be found in the
        ``contracts`` sub-directory of the Django App that holds the model that
        is inheriting from this class (your app)
    """

    contract_name = None
    normalizer_class = Normalizer

    class Meta:
        proxy = True

    def save(self, *args, **kwargs):
        """
        Sets :py:attr:`~djwebdapp_ethereum.models.EthereumTransaction.abi` and
        :py:attr:`~djwebdapp_ethereum.models.EthereumTransaction.bytecode` if
        :py:attr:`contract_name` is set.
        """
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
    """

    class Meta:
        proxy = True


class EthereumEvent(Event):
    contract = models.ForeignKey(
        EthereumContract,
        on_delete=models.CASCADE,
        related_name="contractevent_set",
    )

    def contract_subclass(self):
        return Transaction.objects.get_subclass(pk=self.contract.pk)
