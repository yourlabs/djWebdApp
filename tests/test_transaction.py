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
def transaction_indexer_fail():
    class FailNormalizer(Normalizer):
        @classmethod
        def deploy(cls, transaction, contract):
            raise Exception('FailNormalizer')

    Transaction.normalizer_class = FailNormalizer
    yield Transaction
    Transaction.normalizer_class = None


@pytest.mark.django_db
def test_normalize_error(blockchain, transaction_indexer_fail):
    tx = transaction_indexer_fail(
        blockchain=blockchain, kind='contract')
    tx.save()
    tx.normalize()
