from django.db.models import Q, Sum


def balance_update(fa12, address):
    """
    Account balance calculator.

    We completely recalculate the balance here so that we are able to keep
    correct results even after a blockchain reorg.

    Note that the blockchain implementation is completely out of the way here:
    we're dealing with normalized models!
    """

    # calculate a balance total
    total = fa12.mint_set.exclude(
        # exclude calls deleted by reorg!!
        Q(tezos_call__state='deleted') | Q(ethereum_call__state='deleted')
    ).filter(
        address=address,
    ).aggregate(
        total=Sum('value')
    )['total']

    # you would have to add burn() and transfer() method support here if you
    # had them in your smart contract

    # set the balance for an address
    address.fa12_balance_set.update_or_create(
        fa12=fa12,
        defaults=dict(
            balance=total,
        ),
    )
