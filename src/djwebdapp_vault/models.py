from django.conf import settings
from django.db import models
from django.db.models import signals

from cryptography.hazmat.primitives.ciphers import (
    Cipher,
    algorithms,
    modes,
)
from cryptography.hazmat.backends import default_backend

from mnemonic import Mnemonic

from djwebdapp.models import Address


KEY = settings.SECRET_KEY.encode('utf8')[:32]
while len(KEY) < 32:
    KEY = KEY + KEY[:32 - len(KEY)]
IV = settings.SECRET_KEY.encode('utf8')[-16:]
while len(IV) < 16:
    IV = IV + IV[-16 + len(IV):]


def cipher():
    return Cipher(
        algorithms.AES(KEY),
        modes.CBC(IV),
        backend=default_backend()
    )


def encrypt(secret):
    encryptor = cipher().encryptor()
    return encryptor.update(secret) + encryptor.finalize()


def decrypt(secret):
    decryptor = cipher().decryptor()
    return decryptor.update(secret) + decryptor.finalize()


class Wallet(Address):
    mnemonic = models.TextField()
    revealed = models.BooleanField(default=False)


def generate(sender, instance, **kwargs):
    """
    Generate a default mnemonic
    """
    if instance.mnemonic:
        return

    instance.mnemonic = encrypt(Mnemonic('english').generate(128))
signals.pre_save.connect(generate, sender=Wallet)
