djWebdApp Tezos
~~~~~~~~~~~~~~~

Example contract
================

We will need to instanciate a contract on this blockchain. We'll use a simple
example in actually pure Python with the PyMich compiler.

We have an ``example.py`` contract source code and its compiled version in an
``example.json`` file in ``src/djwebdapp_tezos_example`` directory. This is
what the Python code is like:

.. literalinclude:: ../src/djwebdapp_tezos_example/example.py
  :language: Python

Where you to change it, you would have to recompile it into Micheline JSON with
the following command:

.. code-block:: sh

   pip install pymich
   pymich example.py example.json

Local blockchain and tzkt API
=============================

Instead of using the mainnet, we're going to use a local blockchain, so that
you learn how to test locally. Also, we're going to setup a local tzkt API,
because this is used by the tezos provider to index blockchain data.

We provide a ``docker-compose.yml`` in the ``src/djwebdapp_tezos_example``
directory of this repository, get in there and run ``docker-compose up``.

As some of us will also want to convert this to `GitLab-CI
services <https://docs.gitlab.com/ee/ci/services/>`_\ , we'll refer to our services
by hostname from now on, which is why we add the following to
``/etc/hosts``\ :

.. code-block::

   127.0.0.1 tzlocal tzkt-api

You should then have:

* a local tezos sandbox on ``tzlocal:8732`` which autobakes every second (like
  geth development mode)
* a local tzkt API on ``tzkt-api:5000``

Example contract deployment
===========================

Sandbox ids are predefined and hardcoded, you can find them in the
`tezos-init-sandboxed-client.sh
script <https://gitlab.com/tezos/tezos/-/blob/master/src/bin_client/tezos-init-sandboxed-client.sh>`_.

Let's deploy our example contract using ``pytezos``\ , first install pytezos and
start a python shell:

.. code-block:: sh

   pip install pytezos
   python

In the shell, do the following to have a pytezos client with a sandbox account:

.. code-block:: py

   from pytezos import pytezos
   client = pytezos.using(
       key='edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh',
       shell='http://tzlocal:8732',
   )
   client.account()

This will output something like:

.. code-block::

   {'balance': '3997440000000', 'delegate': 'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx', 'counter': '0'}

Let's deploy our smart contract and call the ``mint()`` entrypoint by pasting the
following in our pytezos python shell started above, which you need to start if
you haven't already to run the following commands:

.. literalinclude:: ../src/djwebdapp_tezos_example/example_origination.py
  :language: Python

This should store the deployed contract address in the address variable, copy
it because you need it to index the contract in the next section.

Indexing a contract
===================

Now that we have deployed a contract, and setup ``djwebdapp`` for a local tezos
node, let's index a contract, also programatically so in ``./manage.py shell``,
declare ``address='<YOUR CONTRACT ADDRESS>`` and run the following code:

.. literalinclude:: ../src/djwebdapp_tezos_example/example_index.py
  :language: Python

This will synchronize the contract using the tzkt API. The ``tries`` argument
is optionnal, and useful for freshly originated contracts, so that it will wait
until it indexes at least one transaction before returning. ``contract.sync()``
returns True if at least one transaction was returned by tzkt for this contract
address.

.. note:: Instead of the above code, we could have added the Blockchain and
          SmartContract in the admin and called ``./manage.py
          index_contracts``.

Normalizing incomming data
==========================

In the ``djwebdapp_tezos_example`` app we have created some sample models to
normalize incomming data, if you want to create your own in your own project
this completely arbitrary code that would go in the ``models.py`` script in a
new app you would have created with ``./manage.py startapp``.

It defines some arbitrary models, intended to be as simple as possible for the
sake of the example and at the same time sufficiently close to realistic use
cases, it registers 2 callbacks for normalization:

* ``call_mint``: is connected to the standard django post_save signal for the
  Call model,
* ``balance_update``: is connected to the ``djwebdapp.signals.contract_indexed``
  signal.

You can verify with the following code in ``./manage.py shell``:

.. code-block:: py

   from djwebdapp.models import SmartContract

   contract.fa12
   # <FA12: KT1Kie724z2jXbbm9AnTaNYsRJeAbax88Hqb>

   contract.fa12.mint_set.all()
   # <QuerySet [<Mint: mint(tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx, 1000)>]>

   from djwebdapp_tezos_example.models import Balance

   Balance.objects.all()
   # <QuerySet [<Balance: tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx balance: 1000>]>

You can see the example source code in question in
``src/djwebdapp_tezos_example/models.py``:

.. literalinclude:: ../src/djwebdapp_tezos_example/models.py
  :language: Python
