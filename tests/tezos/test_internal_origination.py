import mock
import os
import pytest

from pytezos import ContractInterface
from pytezos.contract.result import OperationResult

from djwebdapp_tezos.models import TezosTransaction


@pytest.mark.django_db
def test_internal_operation(client, using, blockchain):
    tz_path = os.path.join(
        os.path.dirname(__file__),
        __file__.replace('.py', '.tz'),
    )
    with open(tz_path, encoding="UTF-8") as mich_file:
        michelson = mich_file.read()

    factory = ContractInterface.from_michelson(michelson).using(**using)

    opg = factory.originate(
        initial_storage=factory.storage.dummy()
    ).send(min_confirmations=1)

    factory_addr = OperationResult.from_operation_group(
        opg.opg_result
    )[0].originated_contracts[0]

    factory = client.contract(factory_addr)

    opg = factory.default(1).send(min_confirmations=1)

    # destination not available when "kind" == "origination"
    assert "destination" not in opg.opg_result["contents"][0]["metadata"]["internal_operation_results"][0]
    assert "origination" == opg.opg_result["contents"][0]["metadata"]["internal_operation_results"][0]["kind"]

    # whereas destination is available when "kind" == "transacion"
    assert opg.opg_result["contents"][0]["destination"]
    assert opg.opg_result["contents"][0]["kind"] == "transaction"


    deployed_counter_contract_address = factory.storage()
    deployed_counter_contract = client.contract(deployed_counter_contract_address)
    originated_address = opg.opg_result["contents"][0]["metadata"]["internal_operation_results"][0]["result"]["originated_contracts"][0]
    assert factory.storage() == originated_address

    # our test scenario is now ready: proceed to actual djwebdapp tests

    contract = TezosTransaction.objects.create(
        blockchain=blockchain,
        address=factory_addr,
    )

    # This mock is used to verify normalize() call order
    from djwebdapp.normalizers import Normalizer
    class TestNormalizer(Normalizer):
        originations = []
        calls = []
        def deploy(self, transaction, contract):
            # second origination is an internal transaction
            # and should have a caller which we should be
            # able to access here
            if len(self.originations):
                assert transaction.caller

            self.originations.append(transaction)

        def default(self, transaction, contract):
            self.calls.append(transaction)

            # our call to the smart contract originated
            # a new smart contract in an internal call.
            # we should be able to access the internal call
            # here.
            assert len(transaction.internal_calls)

    TezosTransaction.indexer_class = TestNormalizer

    blockchain.provider.index()
    contract.refresh_from_db()
    assert contract.hash

    originated = TezosTransaction.objects.get(
        blockchain=blockchain,
        address=originated_address,
    )

    internal = TezosTransaction.objects.get(
        blockchain=blockchain,
        hash=originated.hash,
        contract=contract,
    )

    assert TestNormalizer.originations == [contract, originated]
    assert TestNormalizer.calls == [internal]
