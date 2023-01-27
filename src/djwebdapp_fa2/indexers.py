from django.db.models.signals import post_save
from djwebdapp.models import Account
from djwebdapp_tezos.models import TezosTransaction

from djwebdapp_fa2.models import Balance, Fa2Contract, Fa2Token
from djwebdapp_utils.indexers import AbstractIndexer


class Fa2Indexer(AbstractIndexer):
    def mint(self, fa2_contract, instance, storage, **kwargs):
        token, _ = Fa2Token.objects.update_or_create(
            contract=fa2_contract,
            token_id=instance.args["token_id"],
        )
        owner_account, _ = Account.objects.get_or_create(
            blockchain=instance.blockchain,
            address=instance.args["owner"],
        )
        Balance.objects.update_or_create(
            account=owner_account,
            token=token,
            defaults=dict(
                amount=instance.args["amount_"],
            ),
        )

    def transfer(self, fa2_contract, instance, storage, **kwargs):
        from_account, _ = Account.objects.get_or_create(
            blockchain=instance.blockchain,
            address=instance.args[0]["from_"],
        )

        token = fa2_contract.fa2token_set.filter(
            token_id=instance.args[0]["txs"][0]["token_id"],
        ).first()

        from_balance, _ = Balance.objects.get_or_create(
            account=from_account,
            token=token,
        )

        for transfer in instance.args[0]["txs"]:
            to_account, _ = Account.objects.get_or_create(
                blockchain=instance.blockchain,
                address=transfer["to_"],
            )
            to_balance, created = Balance.objects.get_or_create(
                account=to_account,
                token=token,
            )
            if created:
                to_balance.amount = 0

            from_balance.amount -= transfer["amount"]

            to_balance.amount += transfer["amount"]
            to_balance.save()

        from_balance.save()

    def burn(self, fa2_contract, instance, storage, **kwargs):
        token = fa2_contract.fa2token_set.filter(
            token_id=instance.args["token_id"],
        ).first()

        burner_balance, _ = Balance.objects.get_or_create(
            account=instance.sender,
            token=token,
        )

        burner_balance.amount -= instance.args["token_amount"]
        burner_balance.save()


#post_save.connect(Fa2Indexer(Fa2Contract), sender=TezosTransaction)
Fa2Contract.indexer_class = Fa2Indexer(Fa2Contract)
