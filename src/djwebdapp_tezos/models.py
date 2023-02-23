import os

import dateutil.parser

from pytezos import ContractInterface

from django.db import models
from django.db.models import signals
from django.dispatch import receiver

from djwebdapp.models import Transaction
from djwebdapp.normalizers import Normalizer


class TezosTransaction(Transaction):
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


class TezosContractManager(models.Manager):
    def update_or_create(self, *args, **kwargs):
        if "tezostransaction_ptr" not in kwargs:
            return super().update_or_create(*args, **kwargs)
        else:
            defaults = kwargs["defaults"]
            del kwargs["defaults"]
            lookup_attributes = kwargs

            instance = self.filter(**lookup_attributes).first()
            if not instance:
                instance = self.model(
                    **lookup_attributes,
                    **defaults,
                )
                instance.save_base(raw=True)
                instance.refresh_from_db()
                return instance, True

            self.filter(**lookup_attributes).update(**defaults)
            instance = self.get(**lookup_attributes)
            return instance, False

    def get_or_create(self, *args, **kwargs):
        if "tezostransaction_ptr" not in kwargs:
            return super().get_or_create(*args, **kwargs)
        else:
            instance = self.filter(**kwargs).first()
            if not instance:
                instance = self.model(
                    **kwargs,
                )
                instance.save_base(raw=True)
                instance.refresh_from_db()
                return instance, True

            instance = self.filter(**kwargs).first()
            return instance, False


class TezosContract(TezosTransaction):
    contract_file_name = None
    normalizer_class = Normalizer
    objects = TezosContractManager()

    @property
    def contract_path(self):
        if not self.contract_file_name:
            raise Exception('Please contract_file_name')
        return os.path.join(
            self._meta.app_config.path,
            'michelson',
            self.contract_file_name,
        )

    class Meta:
        proxy = True

    def save(self, *args, **kwargs):
        if self.contract_file_name and not self.micheline:
            self.micheline = self.get_contract_interface().to_micheline()
        return super().save(*args, **kwargs)

    def _get_contract_name(self):
        return self.contract_file_name.split(".")[0]

    def get_contract_interface(self):
        with open(self.contract_path) as michelson:
            return ContractInterface.from_michelson(michelson.read())

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

    def save(self, *args, **kwargs):
        if not self.function:
            self.function = self.entrypoint
        if not self.contract:
            self.contract = self.target_contract
        super().save(*args, **kwargs)

    def update_or_create(self, *args, **kwargs):
        if "tezostransaction_ptr" not in kwargs:
            return super().update_or_create(*args, **kwargs)
        else:
            defaults = kwargs["defaults"]
            del kwargs["defaults"]
            lookup_attributes = kwargs

            instance = self.filter(**lookup_attributes).first()
            if not instance:
                instance = self.model(
                    **lookup_attributes,
                    **defaults,
                )
                instance.save_base(raw=True)
                instance.refresh_from_db()
                return instance, True

            self.filter(**lookup_attributes).update(**defaults)
            instance = self.get(**lookup_attributes)
            return instance, False

    class Meta:
        proxy = True
