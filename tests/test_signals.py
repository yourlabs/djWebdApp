import pytest
from unittest import mock

from django.dispatch import receiver

from djwebdapp.provider import Provider
from djwebdapp.models import Blockchain, Transaction
from djwebdapp.signals import get_args

#from djwebdapp_example.callback import callback, fixture


fixture = ['test']
def callback(transaction, **kwargs):
    return fixture


@pytest.mark.django_db
def test_get_args_signal():
    blockchain = Blockchain.objects.create(
        provider_class='djwebdapp.provider.Provider'
    )
    transaction = Transaction()
    callback = mock.Mock()
    callback.return_value = ['foobar']
    get_args.connect(callback)
    assert blockchain.provider.get_args(transaction) == callback.return_value
    callback.assert_called_once_with(
        transaction=transaction,
        signal=get_args,
        sender=Provider,
    )
    get_args.disconnect(callback)
