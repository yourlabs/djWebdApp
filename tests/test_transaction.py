import pytest

from djwebdapp.models import Transaction


def test_str_name():
    assert str(Transaction(name='test')) == 'test'


def test_str_contract():
    assert str(Transaction(kind='contract', address='test')) == 'test'


def test_str_hash():
    assert str(Transaction(hash='test')) == 'test'


def test_function():
    assert str(Transaction(function='test')) == 'test()'


def test_amount():
    assert str(Transaction(amount=2)) == '2'
    Transaction.unit_smallest = 'XX'
    assert str(Transaction(amount=2)) == '2XX'
    Transaction.unit_smallest = None


def test_pk():
    assert str(Transaction(pk=3)) == '3'
