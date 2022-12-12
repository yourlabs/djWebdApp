import pytest
from djwebdapp.models import Blockchain, Transaction
from djwebdapp_txgraph.models import TransactionEdge, TransactionGraph


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

    tx_1 = Transaction.objects.create(blockchain=blockchain, state="deploy")
    tx_2 = Transaction.objects.create(blockchain=blockchain, state="deploy")
    tx_3 = Transaction.objects.create(blockchain=blockchain, state="deploy")
    tx_4 = Transaction.objects.create(blockchain=blockchain, state="deploy")

    edge_1 = TransactionEdge.objects.create(
        input_node=tx_1,
        output_node=tx_2,
    )

    edge_2 = TransactionEdge.objects.create(
        input_node=tx_1,
        output_node=tx_3,
    )

    edge_3 = TransactionEdge.objects.create(
        input_node=tx_2,
        output_node=tx_4,
    )

    edge_4 = TransactionEdge.objects.create(
        input_node=tx_3,
        output_node=tx_4,
    )

    graph = TransactionGraph.objects.create()
    graph.edges.set([edge_1, edge_2, edge_3, edge_4])

    node_to_deploy = graph.get_next_deploy()
    assert node_to_deploy == tx_1

    tx_1.state = "done"
    tx_1.save()

    node_to_deploy = graph.get_next_deploy()
    assert node_to_deploy == tx_2

    tx_2.state = "done"
    tx_2.save()

    node_to_deploy = graph.get_next_deploy()
    assert node_to_deploy == tx_3

    tx_3.state = "done"
    tx_3.save()

    node_to_deploy = graph.get_next_deploy()
    assert node_to_deploy == tx_4

    tx_4.state = "done"
    tx_4.save()

    node_to_deploy = graph.get_next_deploy()
    assert node_to_deploy == None
