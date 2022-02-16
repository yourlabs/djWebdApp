from django.contrib import admin

from djwebdapp.admin import TransactionAdmin

from .models import EthereumTransaction


@admin.register(EthereumTransaction)
class EthereumTransactionAdmin(TransactionAdmin):
    pass
