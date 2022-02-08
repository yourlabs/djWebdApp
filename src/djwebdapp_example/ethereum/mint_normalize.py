from django.db.models import signals
from djwebdapp_ethereum.models import EthereumTransaction
from djwebdapp_example.balance_update import balance_update


def mint_normalize_ethereum(sender, instance, **kwargs):
    if instance.function != 'mint':
        return

    try:
        fa12 = instance.contract.fa12
    except EthereumTransaction.fa12.RelatedObjectDoesNotExist:
        return

    beneficiary = instance.blockchain.address_set.get(
        address=instance.args['account'],
    )

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
signals.post_save.connect(mint_normalize_ethereum, sender=EthereumTransaction)  # noqa
