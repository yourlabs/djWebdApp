from djwebdapp.models import Account
from djwebdapp.normalizers import Normalizer

from djwebdapp_example_tezos.models import FA12Tezos, FA12TezosMint, FA12TezosBalance


class FA12TezosNormalizer(Normalizer):
    def mint(self, call, contract):
        account, _ = Account.objects.get_or_create(
            address=call.args['_to'],
        )
        call, _ = FA12TezosMint.objects.update_or_create(
            tezostransaction_ptr_id=call.id,
            defaults=dict(
                target_contract=contract,
                mint_account=account,
                mint_amount=call.args['value'],
            )
        )
        balance, _ = FA12TezosBalance.objects.get_or_create(
            account=account,
            fa12=contract,
        )
        balance.balance += call.mint_amount
        balance.save()
