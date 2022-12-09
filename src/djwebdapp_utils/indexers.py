import dateutil.parser

from djwebdapp_tezos.models import TezosTransaction
from djwebdapp_utils.models import IsNormalized
from pytezos.operation.result import OperationResult


class AbstractIndexer:
    def __init__(self, cls):
        self.cls = cls

    def __call__(self, sender, instance: TezosTransaction, **kwargs):
        if instance.state != "done":
            return

        if IsNormalized.objects.filter(transaction=instance, is_normalized=True):
            return

        if not instance.function:
            return

        cls_instance = self.cls.objects.filter(
            origination__address=instance.contract.address
        ).first()

        if not cls_instance:
            return

        try:
            method = getattr(self, instance.function)
        except AttributeError:
            return

        storage = {}
        if instance.metadata:
            tx_op = OperationResult.from_transaction(instance.metadata)

            if instance.contract:
                cls_instance_ci = instance.contract.interface
            elif hasattr(cls_instance, "get_contract_interface"):
                cls_instance_ci = cls_instance.get_contract_interface()
            else:
                raise Exception("No way to retrieve contract interface")

            storage = cls_instance_ci.storage.decode(tx_op.storage)

        kwargs = dict(instance=instance, storage=storage)
        method(cls_instance, **kwargs)

        IsNormalized.objects.update_or_create(
            transaction=instance,
            defaults=dict(
                is_normalized=True,
            ),
        )

    def get_timestamp(self, instance: TezosTransaction):
        endpoint = instance.blockchain.node_set.first().endpoint
        client = instance.sender.provider
        timestamp_str = client.shell.blocks[instance.level].header.shell()["timestamp"]
        return dateutil.parser.isoparse(timestamp_str)
