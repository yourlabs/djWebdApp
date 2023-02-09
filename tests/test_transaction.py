import pytest

from djwebdapp.models import Transaction
from djwebdapp.normalizers import Normalizer


def test_str_name():
    assert str(Transaction(name='test')) == 'test'


def test_str_contract():
    assert str(Transaction(kind='contract', address='test')) == 'test'


def test_str_hash():
    assert str(Transaction(hash='test')) == 'test'


def test_str_function():
    assert str(Transaction(function='test')) == 'test()'


def test_str_amount():
    assert str(Transaction(amount=2)) == '2'
    Transaction.unit_smallest = 'XX'
    assert str(Transaction(amount=2)) == '2XX'
    Transaction.unit_smallest = None


def test_str_pk():
    assert str(Transaction(pk=3)) == '3'


@pytest.fixture
def transaction_normalizer():
    class FailNormalizer(Normalizer):
        fail = False
        @classmethod
        def deploy(cls, transaction, contract):
            if cls.fail:
                raise Exception('FailNormalizer')

    Transaction.normalizer_class = FailNormalizer
    yield Transaction
    Transaction.normalizer_class = None


@pytest.mark.django_db
def test_normalize_error(account, blockchain, transaction_normalizer):
    tx = transaction_normalizer(
        blockchain=blockchain,
        kind='contract',
        sender=account,
    )
    transaction_normalizer.normalizer_class.fail = True
    tx.save()
    tx.normalize()
    assert not tx.normalized
    assert tx.error.startswith('Traceback (most recent call')
    assert tx.error.endswith('Exception: FailNormalizer\n')
    assert tx.last_fail


@pytest.mark.django_db
def test_normalize_success(account, blockchain, transaction_normalizer):
    tx = transaction_normalizer(
        blockchain=blockchain,
        kind='contract',
        sender=account,
    )
    tx.save()
    tx.normalize()
    assert tx.normalized
    assert not tx.error
    assert not tx.last_fail
