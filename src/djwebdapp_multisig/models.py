from django.contrib.auth import get_user_model
from django.db import models
from djwebdapp.models import Account
from djwebdapp_tezos.models import TezosCall, TezosContract


User = get_user_model()


class MultisigContract(TezosContract):
    contract_name = "multisig"
    admin = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="multisigs_administered",
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
    )

    def get_init_storage(self):
        init_storage = self.get_contract_interface().storage.dummy()
        init_storage["admins"] = [self.admin.address]

        return init_storage


class AddAuthorizedContractCall(TezosCall):
    entrypoint = "addAuthorizedContract"
    contract_to_authorize = models.ForeignKey(
        "djwebdapp_tezos.TezosTransaction",
        on_delete=models.CASCADE,
        related_name="add_authorized_contract_calls",
        blank=True,
        null=True,
    )

    def get_args(self):
        return [self.contract_to_authorize.address]
