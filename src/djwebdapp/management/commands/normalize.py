from django.core.management.base import BaseCommand

from djwebdapp.models import Blockchain


class Command(BaseCommand):
    help = 'Normalize indexed transactions'

    def handle(self, *args, **options):
        for blockchain in Blockchain.objects.filter(is_active=True):
            try:
                blockchain.provider.logger.info(f'Normalizing {blockchain}')
                blockchain.provider.normalize()
            except:  # noqa
                blockchain.provider.logger.exception(
                    f'{blockchain}.normalize() failure!'
                )
        else:
            print('Found 0 blockchain to normalize! check is_active')
