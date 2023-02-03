import pytest

from djwebdapp.models import Transaction


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
