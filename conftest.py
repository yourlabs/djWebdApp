import pytest
import os
import sys


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

    path = os.path.join(
        os.path.dirname(__file__),
        'src',
        path,
    )
    for script in scripts:
        script_path = os.path.abspath(os.path.join(path, f'{script}.py'))
        with open(script_path) as f:
            source = f.read()
        try:
            exec(source, variables, variables)
        except:
            _, _, tb = sys.exc_info()
            for name, value in variables.items():
                display = str(value).split('\n')[0]
                print(f'{name}={display}')
            if tb and tb.tb_next:
                print(f'> {script_path}:{tb.tb_next.tb_lineno}')
                print(source.split('\n')[tb.tb_next.tb_lineno - 1])
            else:
                print(f'> {script_path}:?')
                print(source)
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
