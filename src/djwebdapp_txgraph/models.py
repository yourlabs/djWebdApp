from django.db import models
import networkx as nx

from djwebdapp.models import Transaction


class TransactionEdge(models.Model):
    input_node = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="transactiongraphinput_set",
    )
    output_node = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="transactiongraphoutput_set",
    )


class TransactionGraph(models.Model):
    edges = models.ManyToManyField(
        TransactionEdge,
        default=list,
    )

    def get_next_deploy(self):
        edges_qs = self.edges.exclude(output_node__state="done")
        G = nx.DiGraph()
        for edge in edges_qs.select_related("input_node").all():
            if edge.input_node.state != "done":
                breakpoint()
                G.add_edge(edge.input_node_id, edge.output_node_id)
            else:
                G.add_node(edge.output_node_id)

        topological_sort = [node for node in nx.topological_sort(G)]
        if len(topological_sort):
            tx_id = topological_sort[0]
            return Transaction.objects.filter(id=tx_id).first()
        else:
            return None


    def add_edge(self, transactionEdge):
        if not isinstance(transactionEdge, TransactionEdge):
            raise Exception("Function parameters must be instance of TransactionEdge")

        if transactionEdge.output_node.state == 'done':
            raise Exception("Output node is already deployed.")

        G = nx.DiGraph()

        edges_qs = self.edges.exclude(output_node__state="done")
        for edge in edges_qs.select_related("input_node").all():
            if edge.input_node.state != "done":
                G.add_edge(edge.input_node_id, edge.output_node_id)
            else:
                G.add_node(edge.output_node_id)
        
        G.add_edge(transactionEdge.input_node_id, transactionEdge.output_node_id)

        G_undirected = G.to_undirected()
        if not nx.is_connected(G_undirected):
            raise Exception("Adding this edge is going to make the graph disconnected.")

        if not nx.is_directed_acyclic_graph(G):
            raise Exception("Adding this edge is going to make the graph cyclic.")

        self.edges.add(transactionEdge)
