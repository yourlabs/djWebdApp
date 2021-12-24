djWebdApp
~~~~~~~~~

Django is a great web application framework "for perfectionists with deadlines".

A dApp is an app running on the blockchain: a smart contract on which users can
call functions on.

This module provides blockchain support for Django, for reading and/or writing
the blockchain, with the following features usable independently:

* blockchain indexer
* private key vault
* blockchain writer
* blockchain data normalization
* metamask authentication backend
* multiple blockchain support

In addition to these features, djWebdApp differenciates itself from indexers
like dipdup because it is extensible: it's just a module you add to your Django
project like any other Django App, in which you can add models, endpoints, and
have an admin interface for free, and so on, benefiting from the `vast Django
ecosystem of apps <https://djangopackages.org/>`_.

Currently, djwebdapp supports Tezos, new blockchain providers will be
implemented along the way.

Read documentation `online
<https://djwebdapp.rtfd.io>`_ or in the ``docs/`` directory.
