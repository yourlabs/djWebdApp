import pytest
import os


def evil(path, variables=None):
    """
    100% Evil code so that test code be documentation too.

    Example usage::

        variables = {}
        evil('djwebdapp_example/tezos_deploy.py', variables)
        evil('djwebdapp_example/tezos_index.py', variables)

    """
    path = os.path.join(
        os.path.dirname(__file__),
        'src',
        path,
    )
    with open(path) as f:
        source = f.read()
    variables = variables if variables is not None else {}
    result = exec(source, variables, variables)
    return variables


@pytest.fixture
def include():
    return evil
