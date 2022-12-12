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
                G.add_edge(edge.input_node_id, edge.output_node_id)
            else:
                G.add_node(edge.output_node_id)

        topological_sort = [node for node in nx.topological_sort(G)]
        if len(topological_sort):
            tx_id = topological_sort[0]
            return Transaction.objects.filter(id=tx_id).first()
        else:
            return None
