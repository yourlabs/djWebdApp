from django.db import models

from djwebdapp_ethereum.models import (
    EthereumCall,
    EthereumContract,
    EthereumEvent,
)


class FA12Ethereum(EthereumContract):
    contract_name = 'FA12'
    normalizer_class = 'FA12EthereumNormalizer'

    token_name = models.CharField(max_length=200)
    token_symbol = models.CharField(max_length=10)

    def get_args(self):
        return (self.token_name, self.token_symbol)


class FA12EthereumMint(EthereumCall):
    entrypoint = 'mint'
    target_contract = models.ForeignKey(
        'FA12Ethereum',
        on_delete=models.CASCADE,
    )
    mint_account = models.ForeignKey(
        'djwebdapp.Account',
        on_delete=models.CASCADE,
    )
    mint_amount = models.PositiveIntegerField()

    def __str__(self):
        return f'mint({self.mint_account.address}, {self.mint_amount})'

    def get_args(self):
        return (self.mint_account.address, self.mint_amount)


class FA12EthereumBalanceMovement(models.Model):
    event = models.ForeignKey(
        EthereumEvent,
        on_delete=models.CASCADE,
        related_name='fa12_balance_movements',
    )
    fa12 = models.ForeignKey(
        'FA12Ethereum',
        on_delete=models.CASCADE,
    )
    account = models.ForeignKey(
        'djwebdapp.Account',
        on_delete=models.CASCADE,
    )
    amount = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        total_balance = FA12EthereumBalanceMovement.objects.filter(
            account=self.account,
            fa12=self.fa12,
        ).aggregate(
            balance=models.Sum('amount'),
        )['balance']

        FA12EthereumBalance.objects.update_or_create(
            account=self.account,
            fa12=self.fa12,
            defaults=dict(
                balance=total_balance,
            )
        )

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        total_balance = FA12EthereumBalanceMovement.objects.filter(
            account=self.account,
            fa12=self.fa12,
        ).aggregate(
            balance=models.Sum('amount'),
        )['balance']

        FA12EthereumBalance.objects.update_or_create(
            account=self.account,
            fa12=self.fa12,
            defaults=dict(
                balance=total_balance,
            )
        )


class FA12EthereumBalance(models.Model):
    fa12 = models.ForeignKey(
        'FA12Ethereum',
        on_delete=models.CASCADE,
    )
    account = models.ForeignKey(
        'djwebdapp.Account',
        on_delete=models.CASCADE,
    )
    balance = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = (
            ('fa12', 'account'),
        )

    def __str__(self):
        return f'{self.account} balance: {self.balance}'
