from django.db.models import signals
from django.dispatch import receiver

from djwebdapp_ethereum.models import EthereumTransaction
from djwebdapp_example.balance_update import balance_update
from djwebdapp_example.models import FA12


@receiver(signals.post_save, sender=EthereumTransaction)
def mint_normalize_ethereum(sender, instance, **kwargs):
    if instance.function != 'mint':
        # not a mint call? bail out!
        return

    try:
        fa12 = instance.contract.fa12
    except EthereumTransaction.fa12.RelatedObjectDoesNotExist:
        # no FA12 normalized object for this contract? bail out!
        return

    # figure out the beneficiary Account based on the mint call arg _to
    beneficiary = instance.blockchain.account_set.get(
        address=instance.args['account'],
    )

    # create or update the normalized Mint object for this call
    fa12.mint_set.update_or_create(
        ethereum_call=instance,
        defaults=dict(
            address=beneficiary,
            value=instance.args['amount'],
        )
    )

    # we're fully recalculating the balance here in case of a blockchain reorg
    # to ensure the balance is always current
    balance_update(fa12, beneficiary)


@receiver(signals.post_save, sender=FA12)
def fa12_create_ethereum(sender, instance, created, **kwargs):
    """
    Trigger post_save on every call that the contract already has, if any.
    """
    if not created:
        # we're setup already
        return

    if not instance.ethereum_contract:
        # not an ethereum contract
        return

    for call in instance.ethereum_contract.call_set.all():
        call.save()
