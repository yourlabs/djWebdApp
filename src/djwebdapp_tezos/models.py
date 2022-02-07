from pytezos import ContractInterface

from django.db.models.expressions import Value

from djwebdapp.models import SmartContract

from djwebdapp.signals import call_indexed, contract_indexed


def contract_indexed_call_args(sender, instance, **kwargs):
    """
    Fill args for calls indexed prior to contract indexation.
    """
    if 'tezos' not in instance.blockchain.provider_class:
        return

    calls = instance.call_set.filter(function=None)
    if not len(calls):
        # no calls to fix
        return

    interface = ContractInterface.from_micheline(
        instance.metadata['script']['code']
    )

    for call in calls:
        call.function = call.metadata['parameters']['entrypoint']
        method = getattr(interface, call.function)
        args = method.decode(call.metadata['parameters']['value'])
        call.args = args[call.function]
        call.save()
contract_indexed.connect(contract_indexed_call_args)


def call_indexed_call_args(sender, instance, **kwargs):
    """
    Fill args for call if their contract has been indexed.
    """
    if 'script' not in instance.contract.metadata:
        # this call args will be fixed by contract_indexed_call_args
        return
    interface = ContractInterface.from_micheline(
        instance.contract.metadata['script']['code']
    )
    instance.function = instance.metadata['parameters']['entrypoint']
    method = getattr(interface, instance.function)
    instance.args = method.decode(instance.metadata['parameters']['value'])
call_indexed.connect(call_indexed_call_args)
