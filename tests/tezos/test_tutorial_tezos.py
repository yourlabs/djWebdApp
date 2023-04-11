import pytest


@pytest.mark.django_db
def test_tutorial(include, blockchain):
    include(
        'djwebdapp_example_tezos',
        'blockchain',
        'client',
        'wallet_create',
        'deploy_model',
        'normalize',
    )
