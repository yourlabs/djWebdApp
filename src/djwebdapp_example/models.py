from django.db import models

from .ethereum.mint_normalize import mint_normalize_ethereum  # noqa
from .tezos.mint_normalize import mint_normalize_tezos        # noqa


class FA12(models.Model):
    tezos_contract = models.OneToOneField(
        'djwebdapp_tezos.TezosTransaction',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    ethereum_contract = models.OneToOneField(
        'djwebdapp_ethereum.EthereumTransaction',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )


class Mint(models.Model):
    fa12 = models.ForeignKey(
        'FA12',
        on_delete=models.CASCADE,
    )
    tezos_call = models.OneToOneField(
        'djwebdapp_tezos.TezosTransaction',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    ethereum_call = models.OneToOneField(
        'djwebdapp_ethereum.EthereumTransaction',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    address = models.ForeignKey(
        'djwebdapp.Address',
        on_delete=models.CASCADE,
    )
    value = models.PositiveIntegerField()

    def __str__(self):
        return f'mint({self.user}, {self.value})'


class Balance(models.Model):
    fa12 = models.ForeignKey(
        'FA12',
        on_delete=models.CASCADE,
    )
    address = models.ForeignKey(
        'djwebdapp.Address',
        on_delete=models.CASCADE,
        related_name='fa12_balance_set',
    )
    balance = models.PositiveIntegerField()

    class Meta:
        unique_together = (
            ('fa12', 'address'),
        )

    def __str__(self):
        return f'{self.address} balance: {self.balance}'
