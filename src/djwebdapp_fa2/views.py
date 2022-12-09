from rest_framework import generics
from fa2.models import Fa2Token
from fa2.serializers import Fa2TokenSerializer


class Fa2TokenRetrieveAPIView(generics.RetrieveAPIView):
    """
    API endpoint that shows token auctions
    """
    queryset = Fa2Token.objects.all()
    serializer_class = Fa2TokenSerializer

    def get_object(self):
        return (
            Fa2Token.objects.filter(
                contract__origination__address=self.kwargs["token_address"],
                token_id=self.kwargs["token_id"],
            )
            .select_related("contract__origination")
            .select_related("metadata")
            .select_related("metadata__artifact_asset")
            .select_related("metadata__display_asset")
            .select_related("metadata__thumbnail_asset")
            .select_related("metadata__artifact_asset__ipfs_gateway")
            .select_related("metadata__display_asset__ipfs_gateway")
            .select_related("metadata__thumbnail_asset__ipfs_gateway")
            .prefetch_related("metadata__tags")
            .prefetch_related("metadata__creators")
            .prefetch_related("metadata__attributes")
            .prefetch_related("metadata__royalties")
            .prefetch_related("metadata__attributes")
            .first()
        )
