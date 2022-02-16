from django.contrib import admin

from djwebdapp.admin import TransactionAdmin

from .models import TezosTransaction


@admin.register(TezosTransaction)
class TezosTransactionAdmin(TransactionAdmin):
    pass
