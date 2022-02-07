from django.db import models
from django.db.models import signals

from fernet_fields import EncryptedTextField
from mnemonic import Mnemonic

from djwebdapp.models import Address


class Wallet(Address):
    mnemonic = EncryptedTextField()
    revealed = models.BooleanField(default=False)


def generate(sender, instance, **kwargs):
    """
    Generate a default mnemonic
    """
    if instance.mnemonic:
        return
    mnemonic = Mnemonic('english').generate(128)
    instance.mnemonic = mnemonic


signals.pre_save.connect(generate, sender=Wallet)
