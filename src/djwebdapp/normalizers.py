

class Normalizer:
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
