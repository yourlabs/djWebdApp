from rest_framework import serializers

from fa2.models import Fa2Token
from token_metadata.serializers import Tzip21Serializer


class Fa2TokenSerializer(serializers.ModelSerializer):
    address = serializers.CharField(source='contract.origination.address')
    metadata = Tzip21Serializer()

    class Meta:
        model = Fa2Token
        fields = [
            "address",
            "token_id",
            "metadata",
        ]
