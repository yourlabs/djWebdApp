from django.core.management.base import BaseCommand

from djwebdapp.models import Blockchain


class Command(BaseCommand):
    help = 'Synchronize external transactions'

    def handle(self, *args, **options):
        for blockchain in Blockchain.objects.filter(is_active=True):
            try:
                blockchain.provider.index()
            except:  # noqa
                blockchain.provider.logger.exception(
                    f'{blockchain}.provider.index() failure!'
                )
