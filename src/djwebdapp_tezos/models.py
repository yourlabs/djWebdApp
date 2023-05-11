import json
import os

import dateutil.parser

from pytezos import ContractInterface

from django.db import models
from django.db.models import signals
from django.dispatch import receiver

from djwebdapp.models import Transaction
from djwebdapp.normalizers import Normalizer


class TezosTransaction(Transaction):
    """
    Base class for tezos transactions.

    .. py:attribute:: micheline

        Smart contract micheline JSON code.
    """
    unit_smallest = 'xTZ'
    contract = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='call_set',
        null=True,
        blank=True,
        help_text='Smart contract, appliable to method call',
    )
    micheline = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text='Smart contract Micheline, if this is a smart contract',
    )
    caller = models.ForeignKey(
        "TezosTransaction",
        on_delete=models.CASCADE,
        null=True,
        related_name="_internal_calls",
    )

    def save(self, *args, **kwargs):
        """
        Set :py:attr:`~djwebdapp.models.Transaction.has_code` if
        :py:attr:`~micheline`.
        """
        if self.micheline:
            self.has_code = True
        return super().save(*args, **kwargs)

    @property
    def interface(self):
        return ContractInterface.from_micheline(self.micheline)

    @property
    def is_internal(self):
        return bool(self.caller_id)

    @property
    def internal_calls(self):
        if self.is_internal:
            txgroup_internal_calls_qs = self.caller._internal_calls
        else:
            txgroup_internal_calls_qs = self._internal_calls

        tx_internal_calls_qs = txgroup_internal_calls_qs.filter(
            nonce__gte=self.nonce if self.nonce else 0,
            sender__address=self.contract.address,
        )
        return tx_internal_calls_qs.order_by("nonce").all()

    @property
    def storage(self):
        from pytezos.operation.result import OperationResult
        if self.metadata:
            tx_op = OperationResult.from_transaction(self.metadata)
            contract = self.contract_subclass()
            if contract:
                return contract.interface.storage.decode(tx_op.storage)

    @property
    def timestamp(self):
        client = self.provider.client
        timestamp_str = client.shell.blocks[self.level].header.shell()
        return dateutil.parser.isoparse(timestamp_str["timestamp"])


@receiver(signals.pre_save, sender=TezosTransaction)
def contract_micheline(sender, instance, **kwargs):
    if not instance.address or instance.micheline:
        return

    if instance.kind != 'contract':
        return  # only fetch micheline for contracts

    interface = instance.blockchain.provider.client.contract(instance.address)
    instance.micheline = interface.to_micheline()


class TezosContract(TezosTransaction):
    contract_name = None
    normalizer_class = Normalizer

    class Meta:
        proxy = True

    def save(self, *args, **kwargs):
        """
        Set :py:attr:`~djwebdapp_tezos.models.TezosTransaction.micheline` if
        :py:attr:`~djwebdapp.models.Transaction.contract_name` is set.
        """
        if self.contract_name and not self.micheline:
            self.micheline = self.get_contract_interface().to_micheline()
        return super().save(*args, **kwargs)

    def get_contract_interface(self):
        if self.micheline:
            return ContractInterface.from_micheline(self.micheline)
        elif os.path.exists(f'{self.contract_path}.json'):
            with open(f'{self.contract_path}.json') as micheline:
                return ContractInterface.from_micheline(
                    json.loads(micheline.read())
                )
        elif os.path.exists(f'{self.contract_path}.tz'):
            with open(f'{self.contract_path}.tz') as michelson:
                return ContractInterface.from_michelson(michelson.read())
        raise Exception('Contract sources could not be found')

    def get_init_storage(self):
        raise NotImplementedError

    def get_michelson_storage(self):
        contract_interface = self.get_contract_interface()
        return contract_interface.storage.encode(self.get_init_storage())

    def get_args(self):
        return self.get_michelson_storage()


class TezosCall(TezosTransaction):
    entrypoint = None
    normalizer_class = None
    target_contract = None

    class Meta:
        proxy = True
