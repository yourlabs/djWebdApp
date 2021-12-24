from django.contrib.auth.models import User
from django.db import models
from django.db.models import signals, Sum

from djwebdapp.models import Call, SmartContract
from djwebdapp.signals import contract_indexed


class FA12(models.Model):
    contract = models.OneToOneField(
        'djwebdapp.SmartContract',
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return self.contract.address


class Mint(models.Model):
    fa12 = models.ForeignKey(
        'FA12',
        on_delete=models.CASCADE,
    )
    call = models.OneToOneField(
        'djwebdapp.Call',
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        'auth.User',
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
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
    )
    balance = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.user} balance: {self.balance}'


def call_mint(sender, instance, **kwargs):
    if instance.function != 'mint':
        return

    if not instance.sender.owner:
        # let's auto-register the sender user here
        instance.sender.owner, _ = User.objects.get_or_create(
            username=instance.sender.address,
        )
        instance.sender.save()

    beneficiary, _ = User.objects.get_or_create(
        username=instance.args['_to'],
    )

    fa12, _ = FA12.objects.get_or_create(
        contract=instance.contract,
    )
    fa12.mint_set.update_or_create(
        call=instance,
        defaults=dict(
            user=beneficiary,
            value=instance.args['value'],
        )
    )
signals.post_save.connect(call_mint, sender=Call)


def balance_update(sender, instance, **kwargs):
    fa12 = FA12.objects.filter(contract=instance).first()

    if not fa12:
        return

    user_ids = fa12.mint_set.values_list('user', flat=True).distinct()
    for user_id in user_ids:
        total = fa12.mint_set.filter(
            user_id=user_id
        ).aggregate(
            total=Sum('value')
        )['total']
        balance, _ = Balance.objects.update_or_create(
            user_id=user_id,
            fa12=fa12,
            defaults=dict(
                balance=total,
            ),
        )
contract_indexed.connect(balance_update)
