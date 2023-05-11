from djwebdapp.models import Account
from djwebdapp.normalizers import Normalizer

from djwebdapp_example_ethereum.models import FA12Ethereum, FA12EthereumMint, FA12EthereumBalance


class FA12EthereumNormalizer(Normalizer):
    def mint(self, call, contract):
        account, _ = Account.objects.get_or_create(
            address=call.args['account'],
        )
        call, _ = FA12EthereumMint.objects.update_or_create(
            ethereumtransaction_ptr_id=call.id,
            defaults=dict(
                target_contract=contract,
                mint_account=account,
                mint_amount=call.args['amount'],
            )
        )
        balance, _ = FA12EthereumBalance.objects.get_or_create(
            account=account,
            fa12=contract,
        )
        balance.balance += call.mint_amount
        balance.save()
