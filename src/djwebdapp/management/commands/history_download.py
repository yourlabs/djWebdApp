from django.core.management.base import BaseCommand

from djwebdapp.models import Blockchain


class Command(BaseCommand):
    help = '''
    Import a contract from tzkt.

    Example usage:

        ./manage.py history_download 'Tezos Mainnet' <address>
    '''

    def add_arguments(self, parser):
        parser.add_argument(
            'blockchain',
            type=str,
            help='Name of the blockchain to import into'
        )
        parser.add_argument(
            'target',
            type=str,
            help='Id of the contract to import',
        )

    def handle(self, *args, **options):
        blockchain = Blockchain.objects.get(name=options['blockchain'])
        blockchain.provider.download(target=options['target'])
