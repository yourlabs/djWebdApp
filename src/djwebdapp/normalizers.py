

class Normalizer:
    _registry = {}

    def __init_subclass__(cls, /, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._registry[cls.__name__] = cls

    @classmethod
    def normalize(cls, transaction, contract):
        normalizer = cls()
        if transaction.function:
            method = getattr(normalizer, transaction.function, None)
            if method:
                method(transaction, contract)
