from datetime import datetime, timedelta

from django.contrib import auth
from django.db.utils import IntegrityError

from rest_framework.authentication import BasicAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response

from pytezos.crypto.encoding import base58_encode
from pytezos.crypto.key import Key


User = auth.get_user_model()


def string_length_in_hexa_over_four_bytes(message: str) -> str:
    """
    This function takes a string as input and returns its length encoded
    in hexadecimal over 4 bytes.

    - input: a message
    - output: the message length represented in hex over 4 bytes

    example:
    - input: `foobar`
    - output:
        len("abcdefghijklmnopqrstuvwxyz") == 26
        hex(len("abcdefghijklmnopqrstuvwxyz")) == "0x1a"
        hex(len("abcdefghijklmnopqrstuvwxyz"))[2:] == "1a"
        hex(len("abcdefghijklmnopqrstuvwxyz"))[2:].zfill(8) == "0000001a"
    """
    return hex(len(message))[2:].zfill(8)


def encode_message(message: str) -> str:
    """
    Encodes a message to check the signature sent by the backend against
    """
    message = f'Tezos Signed Message: {message}'
    length = string_length_in_hexa_over_four_bytes(message)
    return '0x0501' + length + message.encode().hex()


def decode_airgap_public_key(raw_public_key: str) -> str:
    public_key_raw = bytes.fromhex(raw_public_key)
    return base58_encode(public_key_raw, b'edpk').decode('ascii')


class WalletLogin(ObtainAuthToken):
    authentication_classes = [BasicAuthentication]

    def post(self, request, *args, **kwargs):
        self.serializer_class(
            data=request.data,
            context=dict(request=request)
        )

        try:
            public_key_alphanum = decode_airgap_public_key(
                request._data['public_key']
            )
        except ValueError:
            public_key_alphanum = request._data['public_key']

        message = request._data['message']
        signed_message = request._data['signed_message']

        try:
            message_date = datetime.utcfromtimestamp(int(message))
        except ValueError:
            return Response(
                {
                    'error': f'Could not parse timestamp "{message}"',
                }
            )

        current_timestamp = datetime.utcnow()
        allowed_delta = timedelta(minutes=10)

        try:
            public_key = Key.from_encoded_key(public_key_alphanum)
            encoded_message = encode_message(message)
            public_key.verify(signed_message, encoded_message)
        except ValueError:
            return Response(
                {
                    'error': 'Failed to validate message signature',
                }
            )

        if current_timestamp - message_date > allowed_delta:
            return Response(
                {
                    'error': 'Message expired',
                }
            )

        try:
            user, created = User._default_manager.get_or_create(
                public_key_hash=public_key.public_key_hash(),
                public_key=public_key_alphanum,
                username=public_key.public_key_hash(),
            )
        except IntegrityError:
            return Response(
                {
                    'error': 'User creation failed',
                }
            )

        if created:
            user.password = User.objects.make_random_password()
            user.save()

        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {
                'token': token.key,
                'user_id': user.pk,
                'public_key_hash': user.public_key_hash,
                'username': user.username,
            }
        )
