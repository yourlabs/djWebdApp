import json
import pytest
from pytezos import pytezos, Key, ContractInterface, Unit
from pytezos.contract.result import OperationResult
from djwebdapp.models import Blockchain, Account
from djwebdapp_tezos.models import TezosTransaction
import binascii
from pymich.test import ContractLoader


@pytest.mark.django_db
def test_call_with_amount(client):
    auction = ContractLoader.factory('auction/auction.py')
    auction.storage['bids'][auction.storage['top_bidder']] = 0
    auction_ci = auction.deploy(client)

    blockchain, _ = Blockchain.objects.get_or_create(
        name='Tezos Local',
        provider_class='djwebdapp_tezos.provider.TezosProvider',
    )

    # Add our node to the blockchain
    blockchain.node_set.get_or_create(endpoint='http://tzlocal:8732')

    auction = TezosTransaction.objects.create(
        blockchain=blockchain,
        address=auction_ci.address,
    )

    alice, _ = Account.objects.update_or_create(
        blockchain=blockchain,
        address='tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx',
        defaults=dict(
            secret_key=binascii.b2a_base64(Key.from_encoded_key(
                'edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh'
            ).secret_exponent).decode(),
        ),
    )

    bid = TezosTransaction.objects.create(
        contract=auction,
        sender=alice,
        state="deploy",
        function="bid",
        args=[Unit],
        amount=1_000,
    )
    bid.deploy()

    # wait for transaction to confirm
    blockchain.wait()

    blockchain.provider.index()

    assert auction_ci.storage["bids"][alice.address]() == 1_000
    assert bid.level
