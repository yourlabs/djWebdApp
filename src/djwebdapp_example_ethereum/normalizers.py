from djwebdapp.models import Account
from djwebdapp.normalizers import Normalizer

from djwebdapp_example_ethereum.models import (
    FA12Ethereum,
    FA12EthereumMint,
    FA12EthereumBalance,
    FA12EthereumBalanceMovement,
)


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

    def Mint(self, event, contract):
        account, _ = Account.objects.get_or_create(
            address=event.args['to_'],
            blockchain=contract.blockchain,
        )
        FA12EthereumBalanceMovement.objects.update_or_create(
            event=event,
            defaults=dict(
                fa12=contract,
                account=account,
                amount=event.args['amount_'],
            )
        )

    def reorg_Mint(self, event, contract):
        """
        Called when a Mint event is deleted due to chain reorganization.

        Deletes the associated balance movement and recalculates balances.
        The FA12EthereumBalanceMovement.delete() method handles recalculation.
        """
        try:
            balance_movement = FA12EthereumBalanceMovement.objects.get(
                fa12=contract,
                event=event,
            )
            balance_movement.delete()  # This triggers balance recalculation
        except FA12EthereumBalanceMovement.DoesNotExist:
            pass  # Movement may not exist if event was never normalized
