# we can also refresh balances of all accounts with this method
# you would rather have ./manage.py refresh_balances in a cron or something
new_wallet.refresh_balance()
assert new_wallet.balance == 1_000_000
assert new_wallet.provider.get_balance() == new_wallet.balance
