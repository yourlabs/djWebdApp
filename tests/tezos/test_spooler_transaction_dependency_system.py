import pytest

from djwebdapp_tezos.models import TezosTransaction


@pytest.mark.django_db
def test_spooling_tx_dependency_mecanism(blockchain):
    origination_1 = TezosTransaction.objects.create(blockchain=blockchain, state="deploy")
    origination_2 = TezosTransaction.objects.create(blockchain=blockchain, state="deploy")
    call_1 = TezosTransaction.objects.create(blockchain=blockchain, state="deploy")
    call_2 = TezosTransaction.objects.create(blockchain=blockchain, state="deploy")

    call_1.dependencies.set([origination_1, origination_2])
    call_2.dependencies.set([call_1])

    dependency = blockchain.provider.get_transaction_dependency(call_2)
    assert dependency == origination_2

    origination_1.state = "done"
    origination_1.save()

    dependency = blockchain.provider.get_transaction_dependency(call_2)
    assert dependency == origination_2

    origination_2.state = "done"
    origination_2.save()

    dependency = blockchain.provider.get_transaction_dependency(call_2)
    assert dependency == call_1

    call_1.state = "retry"
    call_1.save()

    dependency = blockchain.provider.get_transaction_dependency(call_2)
    assert dependency == call_1

    call_1.state = "done"
    call_1.save()

    dependency = blockchain.provider.get_transaction_dependency(call_2)
    assert dependency == call_2


@pytest.mark.django_db
def test_aborted_dependency_mecanism(blockchain, alice):
    alice.balance = 10
    alice.save()
    origination_1 = TezosTransaction.objects.create(sender=alice, blockchain=blockchain, state="done", name="origination_1")
    origination_2 = TezosTransaction.objects.create(sender=alice, blockchain=blockchain, state="aborted", name="origination_2")
    origination_3 = TezosTransaction.objects.create(sender=alice, blockchain=blockchain, state="deploy", name="origination_3")
    call_1 = TezosTransaction.objects.create(sender=alice, blockchain=blockchain, state="deploy", name="call_1")
    call_2 = TezosTransaction.objects.create(sender=alice, blockchain=blockchain, state="deploy", name="call_2")
    call_3 = TezosTransaction.objects.create(sender=alice, blockchain=blockchain, state="deploy", name="call_3")

    call_1.dependencies.set([origination_1, origination_2, origination_3])
    call_2.dependencies.set([call_1])
    call_3.dependencies.set([origination_2])

    dependency = blockchain.provider.get_transaction_dependency(call_3)
    assert dependency == [origination_2, call_3]

    dependency = blockchain.provider.get_transaction_dependency(call_2)
    assert dependency == origination_3

    origination_3.state = "done"
    origination_3.save()

    dependency = blockchain.provider.get_transaction_dependency(call_2)
    assert dependency == [call_1, origination_2, call_2]

    blockchain.provider.transaction_class.objects.all().values("name", "state")

    calls = blockchain.provider.get_candidate_calls()
    assert calls == []

    call_1.refresh_from_db()
    assert call_1.state == "aborted"

    call_2.refresh_from_db()
    assert call_2.state == "aborted"

    call_3.refresh_from_db()
    assert call_3.state == "aborted"
