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


@pytest.mark.django_db
def test_add_edge():
    blockchain = Blockchain.objects.create(
        provider_class='djwebdapp_tezos.provider.TezosProvider',
    )

    tx_1 = Transaction.objects.create(blockchain=blockchain, state="deploy")
    tx_2 = Transaction.objects.create(blockchain=blockchain, state="deploy")
    tx_3 = Transaction.objects.create(blockchain=blockchain, state="deploy")
    
    edge_1 = TransactionEdge.objects.create(
        input_node=tx_1,
        output_node=tx_2,
    )

    edge_2 = TransactionEdge.objects.create(
        input_node=tx_1,
        output_node=tx_3,
    )

    graph = TransactionGraph.objects.create()
    graph.add_edge(edge_1)
    graph.add_edge(edge_2)

    assert graph.edges.count() == 2
    assert graph.edges.first() == edge_1
    assert graph.edges.last() == edge_2


@pytest.mark.django_db
def test_add_edge_fails_if_param_is_not_TransactionEdge_instance():
    graph = TransactionGraph.objects.create()

    with pytest.raises(Exception) as exception:
        graph.add_edge("not a TransactionEdge instance")

    assert str(exception.value) == "Function parameters must be instance of TransactionEdge"


@pytest.mark.django_db
def test_add_edge_fails_if_output_node_is_already_deployed():
    blockchain = Blockchain.objects.create(
        provider_class='djwebdapp_tezos.provider.TezosProvider',
    )

    tx_1 = Transaction.objects.create(blockchain=blockchain, state="deploy")
    tx_2 = Transaction.objects.create(blockchain=blockchain, state="done")

    edge = TransactionEdge.objects.create(
        input_node=tx_1,
        output_node=tx_2,
    )

    graph = TransactionGraph.objects.create()

    with pytest.raises(Exception) as exception:
        graph.add_edge(edge)

    assert str(exception.value) == "Output node is already deployed."


@pytest.mark.django_db
def test_add_edge_fails_if_graph_disconnected():
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
        input_node=tx_3,
        output_node=tx_4,
    )

    graph = TransactionGraph.objects.create()
    graph.add_edge(edge_1)

    with pytest.raises(Exception) as exception:
        graph.add_edge(edge_2)

    assert str(exception.value) == "Adding this edge is going to make the graph disconnected."


@pytest.mark.django_db
def test_add_edge_fails_if_graph_has_cycle():
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
        input_node=tx_2,
        output_node=tx_3,
    )

    edge_3 = TransactionEdge.objects.create(
        input_node=tx_3,
        output_node=tx_4,
    )

    edge_4 = TransactionEdge.objects.create(
        input_node=tx_4,
        output_node=tx_1,
    )

    graph = TransactionGraph.objects.create()
    graph.add_edge(edge_1)
    graph.add_edge(edge_2)
    graph.add_edge(edge_3)

    with pytest.raises(Exception) as exception:
        graph.add_edge(edge_4)

    assert str(exception.value) == "Adding this edge is going to make the graph cyclic."
