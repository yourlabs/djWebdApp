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

    def save(self, *args, **kwargs):
        if self.micheline:
            self.has_code = True
        return super().save(*args, **kwargs)

    @property
    def interface(self):
        return ContractInterface.from_micheline(self.micheline)


@receiver(signals.pre_save, sender=TezosTransaction)
def contract_micheline(sender, instance, **kwargs):
    if not instance.address or instance.micheline:
        return

    interface = instance.blockchain.provider.client.contract(instance.address)
    instance.micheline = interface.to_micheline()
