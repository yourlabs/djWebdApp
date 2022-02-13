from django.db import models

from djwebdapp.models import Transaction


class EthereumTransaction(Transaction):
    contract = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='call_set',
        null=True,
        blank=True,
        help_text='Smart contract, appliable to method call',
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
