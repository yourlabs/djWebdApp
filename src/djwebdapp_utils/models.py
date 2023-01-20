import os

import dateutil.parser
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from djwebdapp.models import Account
from djwebdapp.signals import get_args
from djwebdapp_tezos.models import TezosTransaction
from pytezos import ContractInterface, pytezos
from pytezos.operation.result import OperationResult


User = get_user_model()


class AbstractTransaction(models.Model):
    entrypoint: str = NotImplementedError
    target_contract: "AbstractContract" = NotImplementedError

    sender = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        null=True,
    )
    transaction = models.OneToOneField(
        TezosTransaction,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    class Meta:
        abstract = True

    def deploy_transaction(self, sender, instance, **kwargs):
        if not issubclass(type(instance.target_contract), AbstractContract):
            msg = "target_contract foreign key not a subclass of AbstractContract"
            raise Exception(msg)

        if not instance.transaction_id:
            instance.transaction = TezosTransaction.objects.create(
                sender=instance.sender,
                contract=instance.target_contract.origination,
                function=self.entrypoint,
                state="deploy",
                max_fails=10,
                # args will be populated at deploy time
                # via the get_args signal configured below
            )


@receiver(pre_save)
def deploy_transaction(sender, instance, **kwargs):
    if issubclass(sender, AbstractTransaction):
        instance.deploy_transaction(sender, instance, **kwargs)


@receiver(get_args)
def async_arg(transaction, **kwargs):
    wrapped_transaction = get_associated_abstract_class(transaction, AbstractTransaction)
    if wrapped_transaction is not None:
        if hasattr(wrapped_transaction, "get_args"):
            return [wrapped_transaction.get_args()]
    else:
        wrapped_contract = get_associated_abstract_class(transaction, AbstractContract)
        if wrapped_contract is not None:
            return wrapped_contract.get_michelson_storage()


class AbstractContract(models.Model):
    contract_file_name = NotImplementedError
    is_configured = models.BooleanField(default=False)

    sender = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        null=True,
    )
    origination = models.OneToOneField(
        TezosTransaction,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
    )

    class Meta:
        abstract = True

    def _get_app_name(self):
        return type(self).__module__.split(".")[0]

    def _get_contract_name(self):
        return self.contract_file_name.split(".")[0]

    def get_contract_interface(self):
        contract_path = os.path.join(
            os.getcwd(),
            "src",
            self._get_app_name(),
            "michelson",
            self.contract_file_name,
        )
        with open(contract_path) as michelson:
            return ContractInterface.from_michelson(michelson.read())

    def get_init_storage(self):
        raise NotImplementedError

    def get_michelson_storage(self):
        contract_interface = self.get_contract_interface()

        return contract_interface.storage.encode(self.get_init_storage())

    def originate(self, sender, instance, **kwargs):
        if not instance.origination_id:
            instance.origination = TezosTransaction.objects.create(
                sender=instance.sender,
                state="deploy",
                name=self._get_app_name() + "__" + self._get_contract_name(),
                max_fails=10,
                micheline=instance.get_contract_interface().to_micheline(),
                # args will be populated at deploy time. See the get_args
                # signal implemented & connected in this file
            )

    def configure(self):
        pass


@receiver(pre_save)
def originate_contract(sender, instance, **kwargs):
    if issubclass(sender, AbstractContract):
        instance.originate(sender, instance, **kwargs)


def get_associated_abstract_class(instance, abstract_class):
    contract_instance = None
    for field_name in dir(instance):
        if "_" in field_name:
            continue

        try:
            attr = getattr(instance, field_name)
        # should only catch reverse relation errors
        except:  # noqa: E722
            continue

        if issubclass(type(attr), abstract_class):
            if contract_instance is not None:
                raise Exception("TezosTransaction linked to more than 1 AbstractContract/AbstractTransaction subclass.")  # noqa: E501
            contract_instance = attr

    return contract_instance


@receiver(pre_save, sender=TezosTransaction)
def configure_contract(sender, instance, **kwargs):
    if instance.state != "done":
        return

    contract_instance = get_associated_abstract_class(instance, AbstractContract)

    if contract_instance is None:
        return

    if contract_instance.is_configured:
        return

    contract_instance.configure()

    contract_instance.is_configured = True
    contract_instance.save()
