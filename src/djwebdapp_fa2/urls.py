#!/usr/bin/env python3

from django.urls import path

from fa2.views import Fa2TokenRetrieveAPIView


urlpatterns = [
    path(
        "fa2/<str:token_address>/<int:token_id>/",
        Fa2TokenRetrieveAPIView.as_view(),
        name="fa2-detail",
    ),
]
