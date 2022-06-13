from django.contrib import admin
from django.urls import path

from djwebdapp_rest_framework.views import WalletLogin


urlpatterns = [
    path('admin/', admin.site.urls),

    # example wallet login
    path('api-token-auth/', WalletLogin.as_view())
]
