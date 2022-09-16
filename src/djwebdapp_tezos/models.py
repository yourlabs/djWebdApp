from pytezos import ContractInterface

from django.db import models
from django.db.models import signals
from django.dispatch import receiver

from djwebdapp.models import Transaction


class TezosTransaction(Transaction):
    contract = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='call_set',
        null=True,
        blank=True,
        help_text='Smart contract, appliable to method call',
    )
    micheline = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text='Smart contract Micheline, if this is a smart contract',
    )
    caller = models.ForeignKey(
        "TezosTransaction",
        on_delete=models.CASCADE,
        null=True,
        related_name="_internal_calls",
    )

    def save(self, *args, **kwargs):
        if self.micheline:
            self.has_code = True
        return super().save(*args, **kwargs)

    @property
    def interface(self):
        return ContractInterface.from_micheline(self.micheline)

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
        return tx_internal_calls_qs.order_by("nonce").all()


@receiver(signals.pre_save, sender=TezosTransaction)
def contract_micheline(sender, instance, **kwargs):
    if not instance.address or instance.micheline:
        return

    if instance.kind != 'contract':
        return  # only fetch micheline for contracts

    interface = instance.blockchain.provider.client.contract(instance.address)
    instance.micheline = interface.to_micheline()
