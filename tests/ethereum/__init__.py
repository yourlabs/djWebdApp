from djwebdapp_ethereum.models import EthereumTransaction


def deploy_token_proxy(sender):
    with (
        open("./src/djwebdapp_example_ethereum/contracts/Caller.bin") as bytecode,
        open("./src/djwebdapp_example_ethereum/contracts/Caller.abi") as abi,
    ):
        contract = EthereumTransaction.objects.create(
            blockchain=sender.blockchain,
            sender=sender,
            state='deploy',
            bytecode=bytecode.read(),
            abi=abi.read(),
            args=[],
        )
    sender.blockchain.provider.spool()
    contract.refresh_from_db()
    return contract

# Create a call that should deploy afterwards on that contract
def call_token_proxy(
    sender,
    token_proxy,
    token,
    destination_address=None,
    max_fails=10,
):
    if not destination_address:
        destination_address = sender.address
    tx = EthereumTransaction.objects.create(
        sender=sender,
        state='deploy',
        contract=token_proxy,
        function='mintProxy',
        max_fails=max_fails,
        args=(
            token.address,
            destination_address,
            10,
        ),
    )
    sender.blockchain.provider.spool()
    tx.refresh_from_db()
    return tx
