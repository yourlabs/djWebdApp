from django.db.models import Q, Sum


def balance_update(fa12, address):
    total = fa12.mint_set.exclude(
        # exclude calls deleted by reorg!!
        Q(tezos_call__state='deleted') | Q(ethereum_call__state='deleted')
    ).filter(
        address=address,
    ).aggregate(
        total=Sum('value')
    )['total']

    address.fa12_balance_set.update_or_create(
        fa12=fa12,
        defaults=dict(
            balance=total,
        ),
    )
