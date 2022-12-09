from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from djwebdapp.models import Account
from djwebdapp_tezos.models import TezosTransaction
from pytezos import ContractInterface

from djwebdapp_utils.models import AbstractContract, AbstractTransaction


User = get_user_model()


class MultisigContract(AbstractContract):
    contract_file_name = "multisig.tz"
    admin = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="multisigs_administered"
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
    )

    def get_init_storage(self):
        contract_interface = self.get_contract_interface()

        init_storage = contract_interface.storage.dummy()
        init_storage["admins"] = [self.admin.address]

        return init_storage


class AddAuthorizedContractCall(AbstractTransaction):
    entrypoint = "addAuthorizedContract"
    contract_to_authorize = models.ForeignKey(
        TezosTransaction,
        on_delete=models.CASCADE,
        related_name="add_authorized_contract_calls",
        blank=True,
        null=True,
    )
    target_contract = models.ForeignKey(
        MultisigContract,
        on_delete=models.CASCADE,
        related_name="add_authorized_contract_calls",
        blank=True,
        null=True,
    )

    def get_args(self):
        return self.contract_to_authorize.address
