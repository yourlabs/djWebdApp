#!/usr/bin/env python3
import pytest
from pytezos import pytezos


@pytest.mark.django_db
def test_failed_origination():
    """
    should not fail on:
    - https://better-call.dev/ghostnet/opg/ooSaEz2gUfousQxnSjtaR9cU2vWfEBM6NqbHb2qhMkmEcwqn1xo/contents
    - https://better-call.dev/ghostnet/opg/onvtoVURE8AUphiFi39XCYNkh7FHPpnZH71w7s4j715rXNN4Wn1/contents
    """
    failed_originations = [
        {
            "txhash": "onvtoVURE8AUphiFi39XCYNkh7FHPpnZH71w7s4j715rXNN4Wn1",
            "level": 2354661,
        },
        {
            "txhash": "ooSaEz2gUfousQxnSjtaR9cU2vWfEBM6NqbHb2qhMkmEcwqn1xo",
            "level": 2354667,
        },
    ]

    for failed_origination in failed_originations:
        client = pytezos.using(shell="https://ghostnet.tezos.marigold.dev/")

        block = client.shell.blocks[failed_origination["level"]]

        op = block.operations[failed_origination["txhash"]]()
        content = op["contents"][0]

        assert content['kind'] == 'origination'
        assert 'metadata' in content

        from djwebdapp_tezos.provider import TezosProvider
        provider = TezosProvider()

        provider.index_content(failed_origination["level"], 0, op, content)
