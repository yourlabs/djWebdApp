from django.core.management.base import BaseCommand

from djwebdapp.models import Blockchain


class Command(BaseCommand):
    help = 'Synchronize balance'

    def handle(self, *args, **options):
        for blockchain in Blockchain.objects.all():
            for address in blockchain.account_set.all():
                try:
                    address.refresh_balance()
                except Exception as exception:
                    blockchain.provider.logger.exception(exception)
