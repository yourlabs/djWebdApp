import pytest
from decimal import Decimal
from djwebdapp_ethereum.models import EthereumTransaction


@pytest.mark.django_db
def test_index_eth_send_to_contract(include, blockchain):
    variables = include(
        'djwebdapp_example_ethereum',
        'client', 'load', 'deploy', 'blockchain', 'index',
    )

    contract = variables['contract']
    client = variables['client']

    # send eth to contract
    from_address = variables['client'].eth.default_account
    to_address = contract.address
    transfer_amount = Decimal(1)
    tx_hash = client.eth.send_transaction({
        'from': from_address,
        'to': to_address,
        'value': client.to_wei(transfer_amount, 'ether'),
    })

    contract.provider.index()

    assert EthereumTransaction.objects.count() == 3

    transfer_call = EthereumTransaction.objects.order_by("level").last()
    assert transfer_call.amount == transfer_amount
    assert transfer_call.function == 'receive'
    assert transfer_call.args == None
