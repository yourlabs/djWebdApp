"""
Normalizer classes are optionnal helpers to easy contract indexation.
"""


class Normalizer:
    """
    Base Normalizer class.
    """
    _registry = {}
    deploy_method_name = 'deploy'

    def __init_subclass__(cls, /, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._registry[cls.__name__] = cls

    @classmethod
    def normalize(cls, transaction, contract):
        normalizer = cls()
        if transaction.kind == 'function':
            callback_name = transaction.function
        elif transaction.kind == 'contract':
            callback_name = cls.deploy_method_name

        callback = getattr(normalizer, callback_name, None)
        if callback:
            callback(transaction, contract)

    @classmethod
    def normalize_event(cls, event, contract):
        normalizer = cls()
        callback_name = event.name
        callback = getattr(normalizer, callback_name, None)
        if callback:
            callback(event, contract)

    @classmethod
    def reorg_event(cls, event, contract):
        """
        Called when an event is about to be deleted due to chain reorganization.

        Override reorg_{EventName} methods in your normalizer to handle cleanup:

            class MyNormalizer(Normalizer):
                @staticmethod
                def reorg_Transfer(event, contract):
                    # Cleanup domain objects created by Transfer event
                    MyBalance.objects.filter(event=event).delete()
                    # Recalculate aggregates
                    recalculate_balances(event.args['from'])
                    recalculate_balances(event.args['to'])

        Args:
            event: The EthereumEvent being deleted
            contract: The contract that emitted the event
        """
        normalizer = cls()
        callback_name = f'reorg_{event.name}'
        callback = getattr(normalizer, callback_name, None)
        if callback:
            callback(event, contract)
