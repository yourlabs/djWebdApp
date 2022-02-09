djWebdApp Tezos
~~~~~~~~~~~~~~~

Example contract
================

We will need to instanciate a contract on this blockchain. We'll use a simple
example that looks like some FA12, in Pure Python (rather than "Smart" Python),
thanks to Python to Michelson compiler by Thomas Binetruy-Pic, based on Python
AST, Pytezos, and an original idea by your favorite open source zealot:

.. literalinclude:: ../src/djwebdapp_example/tezos/FA12.py
  :language: Python

We already compiled it, but you can change it and recompile it with the
following command:

.. code-block:: sh

   pip install pymich
   cd src/djwebdapp_example/tezos
   pymich FA12.py FA12.json

Local tezos blockchain
======================

.. danger:: Before you begin, make sure you have followed the setup
            instructions from :ref:`Local blockchains`.

Sandbox ids are predefined and hardcoded, you can find them in the
`tezos-init-sandboxed-client.sh
script <https://gitlab.com/tezos/tezos/-/blob/master/src/bin_client/tezos-init-sandboxed-client.sh>`_.

Let's deploy our example contract using `pytezos
<https://pytezos.org>`_, first
install pytezos and start a python shell with the ``./manage.py shell`` command
at the root of our repository:

.. code-block:: sh

   pip install pytezos
   ./manage.py shell

.. note:: The above example also works in a normal Python shell started with
          the ``python`` command, but we need to be in the Django shell of the
          demo project to go through this tutorial anyway.

In the shell, do the following to have a pytezos client with a sandbox account:

.. literalinclude:: ../src/djwebdapp_example/tezos/client.py
  :language: Python

Check your client balance:

.. code-block:: python

    >> client.account()
    {'balance': '3997440000000', 'delegate': 'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx', 'counter': '0'}

Deploy a smart contract
=======================

Let's deploy our smart contract and call the ``mint()`` entrypoint by pasting the
following in our pytezos python shell started above, which you need to start if
you haven't already to run the following commands:

.. literalinclude:: ../src/djwebdapp_example/tezos/deploy.py
  :language: Python

This should store the deployed contract address in the address variable, copy
it or leave the shell open because you need it to index the contract in the
next section.

Setting up a blockchain network
===============================

Now that we have deployed a contract, let's setup ``djwebdapp`` for a local
ethereum node, also programatically in ``./manage.py shell``:

.. literalinclude:: ../src/djwebdapp_example/tezos/blockchain.py
  :language: Python

Indexing a contract
===================

Now that we have deployed a contract, and setup ``djwebdapp`` for a local tezos
node, let's index a contract, also programatically in ``./manage.py shell``:

.. literalinclude:: ../src/djwebdapp_example/tezos/index.py
  :language: Python

Normalizing incomming data: Models
==================================

We have created example models in the ``src/djwebdapp_example`` directory:

.. literalinclude:: ../src/djwebdapp_example/models.py
  :language: Python

.. note:: You wouldn't have to declare ForeignKeys to other Transaction classes
          than TezosTransactions, but we'll learn to do inter-blockchain
          mirroring later in this tutorial, so that's why we have relations to
          both.

And declared a function to update the balance of an FA12 contract:

.. literalinclude:: ../src/djwebdapp_example/balance_update.py
  :language: Python

Normalizing incomming data: Signals
===================================

Finally, to connect the dots, we are first going to connect a custom callback
to ``djwebdapp_tezos.models.TezosTransaction``'s ``post_save`` signal to create
normalized ``Mint`` objects for every ``mint()`` call we index:

.. literalinclude:: ../src/djwebdapp_example/tezos/mint_normalize.py
  :language: Python

We are now ready to normalize the smart contract we have indexed:

.. literalinclude:: ../src/djwebdapp_example/ethereum/normalize.py
  :language: Python
