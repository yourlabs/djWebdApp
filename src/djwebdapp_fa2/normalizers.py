from djwebdapp.models import Account

from djwebdapp_fa2.models import Balance, Fa2Token
from djwebdapp.normalizers import Normalizer


class Fa2Normalizer(Normalizer):
    def mint(self, call, contract):
        token, _ = Fa2Token.objects.update_or_create(
            contract=contract,
            token_id=call.args["token_id"],
        )
        owner_account, _ = Account.objects.get_or_create(
            blockchain=call.blockchain,
            address=call.args["owner"],
        )
        Balance.objects.update_or_create(
            account=owner_account,
            token=token,
            defaults=dict(
                amount=call.args["amount_"],
            ),
        )

    def transfer(self, call, contract):
        from_account, _ = Account.objects.get_or_create(
            blockchain=call.blockchain,
            address=call.args[0]["from_"],
        )

        token = contract.fa2token_set.filter(
            token_id=call.args[0]["txs"][0]["token_id"],
        ).first()

        from_balance, _ = Balance.objects.get_or_create(
            account=from_account,
            token=token,
        )

        for transfer in call.args[0]["txs"]:
            to_account, _ = Account.objects.get_or_create(
                blockchain=call.blockchain,
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

    def burn(self, call, contract):
        token = contract.fa2token_set.filter(
            token_id=call.args["token_id"],
        ).first()

        burner_balance, _ = Balance.objects.get_or_create(
            account=call.sender,
            token=token,
        )

        burner_balance.amount -= call.args["token_amount"]
        burner_balance.save()
