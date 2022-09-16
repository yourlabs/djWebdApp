from django.contrib import admin

from .models import Account, Blockchain, Node, Transaction


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'description',
        'address',
        'owner__username',
    )
    list_display = (
        'address',
        'name',
        'balance',
        'blockchain',
        'last_level',
    )
    list_filter = (
        'blockchain',
        'revealed',
    )
    readonly_fields = (
        'revealed',
        'counter',
        'last_level',
    )

    def get_queryset(self, qs):
        return super().get_queryset(qs).select_related('owner')


@admin.register(Blockchain)
class BlockchainAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'description',
    )
    list_display = (
        'name',
        'is_active',
        'min_level',
        'index_level',
    )
    list_filter = (
        'is_active',
    )


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
    )
    list_display = (
        'endpoint',
        'priority',
        'is_active',
    )
    list_filter = (
        'is_active',
        'blockchain',
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'description',
        'function',
        'hash',
        'sender__address',
        'sender__owner__username',
        'receiver__address',
        'receiver__owner__username',
    )
    list_display = (
        'kind',
        'function',
        'state',
        'name',
        'hash',
        'address',
    )
    list_filter = (
        'kind',
        'state',
        'blockchain',
        'created_at',
        'updated_at',
    )
    readonly_fields = (
        'gas',
        'gasprice',
        'level',
        'last_fail',
        'history',
        'kind',
        'error',
        'has_code',
    )
