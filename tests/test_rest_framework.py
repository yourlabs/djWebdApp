from datetime import datetime
from unittest.mock import Mock

import pytest

from django.contrib import auth
from djwebdapp_rest_framework import views
from rest_framework.test import APIClient
from pytezos.crypto.key import Key


@pytest.mark.django_db
def test_airgap_wallet():
    data = {
        'message': '1644848622',
        'signed_message': 'edsigts6uAiJAU5oRvbBxBFEKMTk21ozxX7ngjXfSinpdhQHKKgVNgd37aRaF6tcvbFUrffzLRYWdSfmt7XrJ638DHZgECxQkee',  # noqa
        'public_key': '3279a2c27e8bc67f43b76eb7f8d57cd47591edeede0387e8164d55706af5c8da'
    }
    url = '/api-token-auth/'

    response = APIClient().post(url, data, format='json')
    assert response.data == {'error': 'Message expired'}


@pytest.mark.django_db
def test_temple_wallet():
    data = {
        'message': '1645436647',
        'signed_message': 'edsigtedLyAiny2uNz5VQpoWn2PdFm8aoLURRR9RByMZGyjGRbGQ63xrFBBpzhvdQZodU4sy3rNTodqWGDqTUDiFf2k9Hxe2ynx',  # noqa
        'public_key': 'edpkuhJRth9s12SApCJBwgdCpcHbjxqth6HXCZBwAnheSoysqKT23R'
    }
    url = '/api-token-auth/'

    response = APIClient().post(url, data, format='json')
    assert response.data == {'error': 'Message expired'}, response.data


@pytest.mark.django_db
def test_kukai_wallet():
    data = {
        'message': '1645439434',
        'signed_message': 'spsig1SbxrnSbkn76G98GZk5BUkYL71dLJuK7E21VjdXtfQn93ad2f8y7Uv5TCXXihf9ybtHTih9PDHetTn8jQ6dcRebJv9i6AZ',  # noqa
        'public_key': 'sppk7d5Q7pPf4u48EyrtHSCCuXx2tBsVRbWXpxGbn8UbUgEQyqBTxhQ'
    }
    url = '/api-token-auth/'

    response = APIClient().post(url, data, format='json')
    assert response.data == {'error': 'Message expired'}


@pytest.mark.django_db
def test_invalid_timestamp():
    data = {
        'message': 'abc',
        'signed_message': 'spsig1SbxrnSbkn76G98GZk5BUkYL71dLJuK7E21VjdXtfQn93ad2f8y7Uv5TCXXihf9ybtHTih9PDHetTn8jQ6dcRebJv9i6AZ',  # noqa
        'public_key': 'sppk7d5Q7pPf4u48EyrtHSCCuXx2tBsVRbWXpxGbn8UbUgEQyqBTxhQ'
    }
    url = '/api-token-auth/'

    response = APIClient().post(url, data, format='json')
    assert response.data == {'error': 'Could not parse timestamp "abc"'}




@pytest.mark.django_db
def test_login(monkeypatch):
    message = str(round(datetime.now().timestamp()))
    encoded_message = views.encode_message(message)
    key = Key.from_encoded_key('edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh')
    signed_message = key.sign(encoded_message)
    key.verify(signed_message, encoded_message)
    data = {
        'message': message,
        'signed_message': signed_message,
        'public_key': key.public_key(),
        'encoded_message': encoded_message,
    }
    url = '/api-token-auth/'

    # we require a user model with public_key and public_key_hash attributes
    # let's mock everything
    User = auth.get_user_model()
    user = User()
    user.public_key_hash = 'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx'
    user.username = 'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx'
    User._default_manager.get_or_create = lambda *a, **k: (user, True)
    User._default_manager.make_random_password = lambda: 'test'
    monkeypatch.setattr(views, 'User', User)

    response = APIClient().post(url, data, format='json')

    assert 'token' in response.data
    assert response.data['user_id'] == 1
    assert response.data['public_key_hash'] == key.public_key_hash()
    assert response.data['username'] == key.public_key_hash()
