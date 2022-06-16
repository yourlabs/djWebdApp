import pytest

from djwebdapp.provider import get_calls_distinct_sender
from djwebdapp.models import Transaction, Blockchain, Account


@pytest.mark.django_db
def test_index(include):
    blockchain, _ = Blockchain.objects.get_or_create(
        name='Tezos Local',
        provider_class='djwebdapp_tezos.provider.TezosProvider',
    )

    # Add our node to the blockchain
    blockchain.node_set.get_or_create(endpoint='http://tzlocal:8732')

    sender_1 = Account.objects.create(blockchain=blockchain)
    sender_2 = Account.objects.create(blockchain=blockchain)
    sender_3 = Account.objects.create(blockchain=blockchain)

    tx1 = Transaction.objects.create(
        blockchain=blockchain,
        function="foo1",
        sender=sender_1,
    )

    tx2 = Transaction.objects.create(
        blockchain=blockchain,
        function="foo2",
        sender=sender_2,
    )

    tx3 = Transaction.objects.create(
        blockchain=blockchain,
        function="foo3",
        sender=sender_3,
    )

    Transaction.objects.create(
        blockchain=blockchain,
        function="foo4",
        sender=sender_1,
    )

    txs = Transaction.objects.all().order_by("created_at")

    distinct_sender_tx = get_calls_distinct_sender(txs, 10)
    assert tx1 in distinct_sender_tx
    assert tx2 in distinct_sender_tx
    assert tx3 in distinct_sender_tx
    assert len(distinct_sender_tx) == 3

    distinct_sender_tx = get_calls_distinct_sender(txs, 2)
    assert tx1 in distinct_sender_tx
    assert tx2 in distinct_sender_tx
    assert len(distinct_sender_tx) == 2
