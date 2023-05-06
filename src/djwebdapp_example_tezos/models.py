from django.db import models

from djwebdapp_tezos.models import TezosCall, TezosContract


class FA12Tezos(TezosContract):
    contract_name = 'FA12'
    normalizer_class = 'FA12TezosNormalizer'
    token_name = models.CharField(max_length=200)
    token_symbol = models.CharField(max_length=10)

    def get_init_storage(self):
        return dict(
            tokens={},
            total_supply=0,
            owner=self.sender.address,
        )


class FA12TezosMint(TezosCall):
    entrypoint = 'mint'
    target_contract = models.ForeignKey(
        'FA12Tezos',
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
        return dict(
            _to=self.mint_account.address,
            value=self.mint_amount,
        )


class FA12TezosBalance(models.Model):
    fa12 = models.ForeignKey(
        'FA12Tezos',
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
