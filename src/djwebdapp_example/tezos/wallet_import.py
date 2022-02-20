# import a bootstrap wallet by secret key
from djwebdapp.models import Account
from pytezos import Key

# Use update_or_create, in case we already have this address!
import binascii
bootstrap, _ = Account.objects.update_or_create(
    blockchain=blockchain,
    address='tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
    defaults=dict(
        secret_key=binascii.b2a_base64(Key.from_encoded_key(
            'edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh'
        ).secret_exponent).decode(),
    ),
)

# balance was automatically fetched
assert bootstrap.balance > 0
old_balance = bootstrap.balance
