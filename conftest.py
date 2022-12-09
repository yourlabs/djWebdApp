import binascii
import pytest
import os
import sys

from pytezos import Key

from djwebdapp.models import Account, Blockchain
from djwebdapp_tezos.models import TezosTransaction


def evil(path, *scripts, variables=None):
    """
    100% Evil code so that test code be documentation too.

    Example usage::

        variables = include(
            'djwebdapp_example/tezos',
            'client', 'deploy', 'blockchain', 'index', 'normalize',
        )

    Or (old syntax)::

        variables = {}
        evil('djwebdapp_example/tezos_deploy.py', variables)
        evil('djwebdapp_example/tezos_index.py', variables)
    """
    variables = variables if variables is not None else {}

    def abspath(script):
        return os.path.abspath(os.path.join(path, f'{script}.py'))

    path = os.path.join(
        os.path.dirname(__file__),
        'src',
        path,
    )
    for number, script in enumerate(scripts, start=0):
        script_path = abspath(script)
        with open(script_path) as f:
            source = f.read()
        try:
            exec(source, variables, variables)
        except:
            exctype, exc, tb = sys.exc_info()
            print('\n\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            print('EXCEPTION IN INCLUDE: START DUMP =====================')
            if number:
                print('Executed successfuly:')
                for i in range(0, number):
                    print(abspath(scripts[i]))
                print('------------------------------------------------------')
            print('FAILED:')
            if tb and tb.tb_next:
                print(f'> {script_path}:{tb.tb_next.tb_lineno}')
                print(source.split('\n')[tb.tb_next.tb_lineno - 1])
            else:
                print(f'> {script_path}:?')
            print(f'{exctype} {exc}')
            print('------------------------------------------------------')
            print('VARIABLES:')
            for name, value in variables.items():
                if name.startswith('__'):
                    continue  # skip builtins
                if name[0] == name.capitalize()[0]:
                    continue  # skip classes
                display = str(value).split('\n')[0][:100]
                print(f'{name}={display}')
            print('------------------------------------------------------')
            print('SOURCE:')
            for number, line in enumerate(source.split('\n'), start=1):
                print(f'{number} {line}')
            print('END DUMP =============================================')
            raise
    return variables


@pytest.fixture
def include():
    return evil


@pytest.fixture
def admin_smoketest(admin_client):
    def _():
        urls = (
            '/admin/djwebdapp/account/',
            '/admin/djwebdapp/account/add/',
            '/admin/djwebdapp/blockchain/',
            '/admin/djwebdapp/blockchain/add/',
            '/admin/djwebdapp/node/',
            '/admin/djwebdapp/node/add/',
            '/admin/djwebdapp/transaction/',
            '/admin/djwebdapp/transaction/add/',
            '/admin/djwebdapp_tezos/tezostransaction/',
            '/admin/djwebdapp_tezos/tezostransaction/add/',
            '/admin/djwebdapp_ethereum/ethereumtransaction/',
            '/admin/djwebdapp_ethereum/ethereumtransaction/add/',
        )
        for url in urls:
            assert admin_client.get(url).status_code == 200
    return _


@pytest.fixture
@pytest.mark.django_db
def wait_transaction():
    def f(transaction: TezosTransaction, no_assert=False):
        res = transaction.blockchain.provider.spool()
        if not no_assert:
            assert res == transaction
        transaction.refresh_from_db()
        transaction.blockchain.wait_level(transaction.level + 2)
        transaction.blockchain.provider.index()
        transaction.refresh_from_db()

    return f


@pytest.fixture
@pytest.mark.django_db
def blockchain():
    configuration = {
        "bcd_api_host": "http://localhost:14000/",
        "bcd_network_name": "sandboxnet",
    }
    blockchain, _ = Blockchain.objects.get_or_create(
        name='Tezos Local',
        provider_class='djwebdapp_tezos.provider.TezosProvider',
        configuration=configuration,
        min_confirmations=1,
    )

    # Add our node to the blockchain
    blockchain.node_set.get_or_create(endpoint='http://tzlocal:8732')

    blockchain.index_level = blockchain.provider.head
    blockchain.save()

    return blockchain


@pytest.fixture
@pytest.mark.django_db
def alice(blockchain):
    alice, _ = Account.objects.update_or_create(
        blockchain=blockchain,
        address='tz1Yigc57GHQixFwDEVzj5N1znSCU3aq15td',
        defaults=dict(
            secret_key=binascii.b2a_base64(Key.from_encoded_key(
                'edsk3EQB2zJvvGrMKzkUxhgERsy6qdDDw19TQyFWkYNUmGSxXiYm7Q'
            ).secret_exponent).decode(),
        ),
    )

    return alice
