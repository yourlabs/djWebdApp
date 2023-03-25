"""
Normalizer classes are optionnal helpers to easy contract indexation.

Normalization is the process of transforming incomming data into structured
relational data. While barely indexing transaction data from the blockchain may
be enough for some simple use cases, usually you'll need to normalize that data
into a structured relational database: your own models.

In djwebdapp, you're going to make a :py:class:`~djwebdapp.models.Transaction`
subclass to represent your Contracts and Contract calls, this will help making
specific endpoints and build a rich web frontend.

However, for complex smart contract architectures, you're going to be writting
a lot of code to process incomming data into normalized models. This code will
have to be somewhere, and normalizers are the elegant solution solution
provided by djwebdapp.

You can subclass the base :py:class:`Normalizer` class for each of your smart
contracts, if you have, like in our examples, an
:py:class:`djwebdapp_fa2.models.Fa2Contract` model, then a bunch of things can
happen on the blockchain such as `mint()`, `transfer()` or `burn()` calls.

In this case, you should subclass :py:class:`Normalizer` into a new
:py:class:`~djwebdapp_fa2.normalizers.Fa2Normalizer` class that you'd declare
in your app's `normalizers` module, in our case `djwebdapp_fa2.normalizers`, so
that it's automatically discovered by `djwebdapp` which will attempt to import
the `normalizers` module of each installed app.
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
