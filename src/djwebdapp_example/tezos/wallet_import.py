# import a bootstrap wallet by secret key
from djwebdapp.models import Account
from pytezos import Key
bootstrap = Account.objects.create(
    secret_key=Key.from_encoded_key(
        'edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh'
    ).secret_exponent,
    blockchain=blockchain,
)

# balance was automatically fetched
assert bootstrap.balance > 0
old_balance = bootstrap.balance
