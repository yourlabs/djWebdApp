from django.db.models import signals
from django.dispatch import receiver

from djwebdapp_tezos.models import TezosTransaction
from djwebdapp_example.balance_update import balance_update
from djwebdapp_example.models import FA12


@receiver(signals.post_save, sender=TezosTransaction)
def mint_normalize_tezos(sender, instance, **kwargs):
    if instance.function != 'mint':
        # not a mint call? bail out!
        return

    try:
        fa12 = instance.contract.fa12
    except TezosTransaction.fa12.RelatedObjectDoesNotExist:
        # no FA12 normalized object for this contract? bail out!
        return

    # figure out the beneficiary Address based on the mint call arg _to
    beneficiary = instance.blockchain.address_set.get(
        address=instance.args['_to'],
    )

    # create or update the normalized Mint object for this call
    fa12.mint_set.update_or_create(
        tezos_call=instance,
        defaults=dict(
            address=beneficiary,
            value=instance.args['value'],
        )
    )

    # we're fully recalculating the balance here in case of a blockchain reorg
    # to ensure the balance is always current
    balance_update(fa12, beneficiary)


@receiver(signals.post_save, sender=FA12)
def fa12_create_tezos(sender, instance, created, **kwargs):
    """
    Trigger post_save on every call that the contract already has, if any.
    """
    if not created:
        # we're setup already
        return

    if not instance.tezos_contract:
        # not a tezos contract
        return

    for call in instance.tezos_contract.call_set.all():
        call.save()
