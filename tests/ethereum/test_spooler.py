import pytest

from tests.ethereum import call_token_proxy, deploy_token_proxy


@pytest.mark.django_db
def test_save_tx_error(include, blockchain_with_event_provider, client):
    include(
        'djwebdapp_example_ethereum',
        'client',
        'blockchain_with_event_provider',
        'account',
        'deploy_model',
    )

    token = blockchain_with_event_provider.transaction_set.exclude(address=None).first().contract_subclass()
    token_proxy = deploy_token_proxy(token.sender)
    ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'
    tx = call_token_proxy(token.sender, token_proxy, token, ZERO_ADDRESS, max_fails=3)

    assert tx.error == 'execution reverted: ERC20: mint to the zero address'

    with pytest.raises(Exception):
        blockchain_with_event_provider.provider.spool()
    tx.refresh_from_db()
    assert tx.error == 'execution reverted: ERC20: mint to the zero address'

    with pytest.raises(Exception):
        blockchain_with_event_provider.provider.spool()
    tx.refresh_from_db()
    assert tx.error == 'Aborting because >= 3 failures, last error: execution reverted: ERC20: mint to the zero address'
