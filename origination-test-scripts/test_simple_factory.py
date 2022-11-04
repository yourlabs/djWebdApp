from pytezos import pytezos
from pytezos import ContractInterface
from pytezos.contract.result import OperationResult


ALICE_KEY = "edsk3EQB2zJvvGrMKzkUxhgERsy6qdDDw19TQyFWkYNUmGSxXiYm7Q"
using_params = dict(key=ALICE_KEY, shell="http://tzlocal:8732")
#using_params = dict(key=ALICE_KEY, shell="https://ghostnet.tezos.marigold.dev/")

pytezos = pytezos.using(**using_params)

with open("/tmp/simple_factory.tz", encoding="UTF-8") as mich_file:
    michelson = mich_file.read()

factory = ContractInterface.from_michelson(michelson).using(**using_params)
opg = factory.originate(initial_storage=factory.storage.dummy()).send(min_confirmations=1)
factory_addr = OperationResult.from_operation_group(opg.opg_result)[0].originated_contracts[0]
factory = pytezos.contract(factory_addr)

opg = factory.default().send(min_confirmations=1)


# destination not available when "kind" == "origination"
assert "destination" not in opg.opg_result["contents"][0]["metadata"]["internal_operation_results"][0]
assert "origination" == opg.opg_result["contents"][0]["metadata"]["internal_operation_results"][0]["kind"]

# whereas destination is available when "kind" == "transacion"
assert opg.opg_result["contents"][0]["destination"]
assert opg.opg_result["contents"][0]["kind"] == "transaction"


deployed_counter_contract_address = factory.storage()
deployed_counter_contract = pytezos.contract(deployed_counter_contract_address)
assert factory.storage() == opg.opg_result["contents"][0]["metadata"]["internal_operation_results"][0]["result"]["originated_contracts"][0]
