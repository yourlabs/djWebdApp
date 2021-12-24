from pytezos import pytezos

from django.core.management.base import BaseCommand

from djwebdapp.models import SmartContract


class Command(BaseCommand):
    help = 'Index contracts transactions'

    def handle(self, *args, **options):
        contracts = SmartContract.objects.filter(blockchain__is_active=True)
        for contract in contracts:
            contract.sync()
