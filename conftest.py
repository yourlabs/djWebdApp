import pytest
import os


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
        with open(os.path.join(path, f'{script}.py')) as f:
            source = f.read()
        exec(source, variables, variables)
    return variables


@pytest.fixture
def include():
    return evil
