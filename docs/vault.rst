djWebdApp Vault Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Setup
=====

Follow the installation steps in this precise order:

- Make sure you have installed djwebdapp with the ``[vault]`` dependencies (or
  ``[all]``).
- Add to ``settings.INSTALLED_APPS``: ``djwebdapp_vault``,
- Run ``./manage.py migrate``,

.. note:: You may rotate Fernet keys used for encryption, please refer to
          `django-fernet-fields
          <https://django-fernet-fields.readthedocs.io/en/latest/#keys>`_
          documentation.

Create a wallet
===============

To write the blockchain, you will need to add a node to your blockchain and then
Add
``djtezos_vault`` to your ``INSTALLED_APPS`` settings and run ``./manage.py migrate``.

Then, create a new wallet in a blockchain:

.. code-block:: py

    from djwebdapp.models import Blockchain
    from djwebdapp_vault.models import Wallet


    wallet = Wallet.objects.create(
        blockchain=Blockchain.objects.first(),
    )

Deploy a contract
=================
