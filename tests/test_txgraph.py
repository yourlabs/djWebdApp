import pytest
from djwebdapp.models import Blockchain, Transaction


@pytest.mark.django_db
def test_get_next_deploy():
    """
    tx_1
    /  \
  tx_2 tx_3
    \  /
    tx_4
    """
    blockchain = Blockchain.objects.create(
        provider_class='djwebdapp_tezos.provider.TezosProvider',
    )

    tx1 = Transaction.objects.create(blockchain=blockchain, state="deploy", name='tx1')
    tx2 = Transaction.objects.create(blockchain=blockchain, state="deploy", name='tx2')
    tx3 = Transaction.objects.create(blockchain=blockchain, state="deploy", name='tx3')
    tx4 = Transaction.objects.create(blockchain=blockchain, state="deploy", name='tx4')

    tx1.dependency_add(tx2)
    tx1.dependency_add(tx3)
    tx2.dependency_add(tx4)
    tx3.dependency_add(tx4)

    assert tx1.dependency_get() == tx4
    tx4.state = 'done'
    tx4.save()

    assert tx1.dependency_get() == tx2
    tx2.state = 'done'
    tx2.save()

    assert tx1.dependency_get() == tx3
    tx3.state = 'done'
    tx3.save()

    assert tx1.dependency_get() == tx1
