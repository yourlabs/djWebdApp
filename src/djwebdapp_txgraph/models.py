from django.db import models
import networkx as nx


class TransactionEdge(models.Model):
    graph = models.ForeignKey(
        'TransactionGraph',
        on_delete=models.CASCADE,
    )
    input_node = models.ForeignKey(
        'djwebdapp.Transaction',
        on_delete=models.CASCADE,
        related_name="transactiongraphinput_set",
    )
    output_node = models.ForeignKey(
        'djwebdapp.Transaction',
        on_delete=models.CASCADE,
        related_name="transactiongraphoutput_set",
    )


class TransactionGraph(models.Model):
    def get_next_deploy(self):
        edges_qs = self.transactionedge_set.exclude(output_node__state="done")
        G = nx.DiGraph()
        for edge in edges_qs.select_related("input_node").all():
            if edge.input_node.state != "done":
                G.add_edge(edge.input_node_id, edge.output_node_id)
            else:
                G.add_node(edge.output_node_id)

        topological_sort = [node for node in nx.topological_sort(G)]
        if len(topological_sort):
            tx_id = topological_sort[0]
            from djwebdapp.models import Transaction
            tx = Transaction.objects.filter(
                id=tx_id,
            ).select_subclasses().first()
            return tx
        else:
            return None
