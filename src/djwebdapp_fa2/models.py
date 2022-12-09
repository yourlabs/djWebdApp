from django.db import models
from djwebdapp.models import Account
from djwebdapp_multisig.models import AddAuthorizedContractCall, MultisigContract

from djwebdapp_utils.models import AbstractTransaction, AbstractContract



class MultisigedAbstractContract(AbstractContract):
    multisig = models.ForeignKey(
        MultisigContract,
        on_delete=models.SET_NULL,
        null=True,
    )

    class Meta:
        abstract = True


class Fa2Contract(MultisigedAbstractContract):
    contract_file_name = "fa2.tz"
    manager = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="fa2_administered",
        null=True,
    )
    metadata_uri = models.CharField(max_length=500)
    name = models.CharField(max_length=100, default="")

    def get_init_storage(self):
        contract_interface = self.get_contract_interface()

        init_storage = contract_interface.storage.dummy()
        init_storage["manager"] = self.manager.address
        init_storage["multisig"] = self.multisig.origination.address
        init_storage["metadata"] = {
            "": self.metadata_uri.encode(),
        }
        init_storage["ledger"] = {}

        return init_storage

    def configure(self):
        AddAuthorizedContractCall.objects.create(
            sender=self.sender,
            contract_to_authorize=self.origination,
            target_contract=self.multisig,
        )


class Fa2Token(models.Model):
    token_id = models.IntegerField()
    metadata_uri = models.CharField(max_length=500)
    contract = models.ForeignKey(
        Fa2Contract,
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = ("token_id", "contract")


class MintCall(AbstractTransaction):
    entrypoint = "mint"
    target_contract = models.ForeignKey(
        Fa2Contract,
        on_delete=models.CASCADE,
    )

    owner = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="mintcall_owner_set",
    )
    token_id = models.PositiveBigIntegerField()
    amount = models.PositiveBigIntegerField()
    metadata_uri = models.CharField(max_length=500)

    def get_args(self):
        return {
            "token_id": self.token_id,
            "amount_": self.amount,
            "owner": self.owner.address,
            "token_metadata": {
                "": self.metadata_uri.encode(),
            },
        }


class UpdateProxyCall(AbstractTransaction):
    entrypoint = "updateProxy"
    target_contract = models.ForeignKey(
        Fa2Contract,
        on_delete=models.CASCADE,
    )

    remove_proxy = models.BooleanField(default=False)
    proxy = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="fa2contract_proxy_set",
    )

    def get_args(self):
        variant_type = "add_proxy"
        if self.remove_proxy:
            variant_type = "remove_proxy"

        return {variant_type: self.proxy.address}


class Balance(models.Model):
    token = models.ForeignKey(
        Fa2Token,
        on_delete=models.CASCADE,
    )
    account = models.ForeignKey(
        Account,
        related_name="fa2_balances",
        on_delete=models.CASCADE,
    )
    amount = models.PositiveBigIntegerField(default=0)

    class Meta:
        unique_together = ("token", "account")
