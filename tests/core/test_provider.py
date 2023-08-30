import pytest

from djwebdapp.models import Account, Blockchain, Transaction


@pytest.mark.django_db
def test_excluded_states():
    # We test the `djwebdapp.provider` methods using the Tezos subclass,
    # but the ETH subclass could be used just as well. We cannot use the
    # provider with the raw `Transaction` model since it does not define
    # a `contract` attribute and lets its subclasses do it and it is needed
    # for the `provider.spool_calls` to work.
    blockchain = Blockchain.objects.create(
        name='tzlocal',
        provider_class='djwebdapp_tezos.provider.TezosProvider',
    )
    blockchain.node_set.get_or_create(endpoint='http://tzlocal:8732')
    account = Account.objects.create(
        name='account',
        blockchain=blockchain,
        balance=100,
        last_level=0,
    )
    provider = blockchain.provider

    excluded_states = ['held', 'aborted', 'confirm', 'done']
    for state in excluded_states:
        provider.transaction_class.objects.create(
            sender=account,
            blockchain=blockchain,
            state=state,
            kind='transfer',
        )

    assert not len(provider.spool_transfers())

    for state in excluded_states:
        contract = provider.transaction_class.objects.create(
            sender=account,
            blockchain=blockchain,
            state=state,
            kind='contract',
            has_code=True,
        )

    assert not len(provider.spool_contracts())

    contract.address = "KT1TxqZ8QtKvLu3V3JH7Gx58n7Co8pgtpQU5"
    contract.save()
    for state in excluded_states:
        provider.transaction_class.objects.create(
            sender=account,
            blockchain=blockchain,
            contract=contract,
            state=state,
            kind='function',
            has_code=True,
        )

    assert not len(provider.spool_calls())

    # The state for all transactions is now set to `deploy` where we should
    # recover all relevant transactions when calling spooling methods.
    # This ensures that the above code was indeed filtered only on the tx state
    provider.transaction_class.objects.update(state='deploy')

    assert len(provider.spool_transfers()) == 4
    assert len(provider.spool_calls()) == 4

    # one TezosTransaction has an address, so `spool_contracts` only
    # returns 3
    assert len(provider.spool_contracts()) == 3
