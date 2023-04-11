djWebdApp Tezos
~~~~~~~~~~~~~~~

.. danger:: Before you begin, make sure you have followed the setup
            instructions from :ref:`Local blockchains`.

Setup
=====

Blockchain
----------

Now that we have deployed a contract, let's setup ``djwebdapp`` for a local
tezos node, also programatically in ``./manage.py shell``:

.. literalinclude:: ../src/djwebdapp_example_tezos/blockchain.py
  :language: Python

Pytezos Client
--------------

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

With the tezos sandbox, we'll use the default account which is already
provisionned with some ethers.

Let's deploy our example contract using `Web3py
<https://web3py.readthedocs.io>`_, install it and start a Python shell with the
``./manage.py shell`` command at the root of our repository:

Account
-------

.. note:: You may rotate Fernet keys used for encryption, please refer to
          `djfernet
          <https://djfernet.readthedocs.io/en/latest/#keys>`_
          documentation.

.. literalinclude:: ../src/djwebdapp_example/tezos/wallet_create.py
  :language: Python

Smart contract
--------------

In this tutorial, we'll use a simple example smart contract in solidity that
looks like some FA12:

.. literalinclude:: ../src/djwebdapp_example_tezos/tezos/FA12.sol
  :language: Solidity

We already compiled it, but you can change it and recompile it with the
following command:

.. code-block:: sh

    cd src/djwebdapp_example_tezos/tezos
    solc --abi --overwrite --output-dir . --bin FA12.sol

What matters is that the contract `.abi` and `.bin` files have matching names
and are both present in the `tezos` sub-directory of the Django app where
corresponding models are going to live.

Models
======

Along with our smart contract, we're creating some models to normalize all the
data both ways: to deploy transactions, as well as to index them.

``FA12Tezos``
    Subclass of
    :py:class:`~djwebdapp_tezos.models.TezosTransaction` and defines
    k:py:attr:`~djwebdapp_tezos.models.TezosContract.contract_file_name`
    as well as
    :py:attr:`~djwebdapp_tezos.models.tezosContract.normalizer_class`,
    which we'll define in the next chapter

``FA12MintTezos``
    Subclass of
    :py:class:`~djwebdapp_tezos.models.TezosCall` and defines
    :py:attr:`~djwebdapp_tezos.models.TezosCall.entrypoint`

Note that both models define a
:py:meth:`~djwebdapp_tezos.models.TezosTransaction.get_args()` method to
return the arguments that the blockchain client should use when deploying.

.. literalinclude:: ../src/djwebdapp_example_tezos/models.py
  :language: Python

Contract deployment
===================

Time to see the beauty of all this, to deploy this smart contract, and make a
bunch of mint calls through Django models!

.. literalinclude:: ../src/djwebdapp_example_tezos/deploy_model.py
  :language: Python

Indexing and normalization
==========================

Indexing is the process of parsing data from the blockchain, normalization is
the process of transforming incomming data into structured relational data.

First, let's call a smart contract function from outside djwebdapp, it's
the call that we are going to index and normalize:

.. literalinclude:: ../src/djwebdapp_example_tezos/deploy_client.py
  :language: Python

To map incomming blockchain data into models, we'll define a
:py:class:`~djwebdapp.normalizers.Normalizer` for that contract, in a
``normalizers.py`` file in the same app, and define a method par contract
function that will be called by the indexer to normalize the data into your
models:

.. literalinclude:: ../src/djwebdapp_example_tezos/normalizers.py
  :language: Python

All we have to do now is call the indexer:

.. literalinclude:: ../src/djwebdapp_example_tezos/index.py
  :language: Python

Example contract deployment
---------------------------

Deploy a smart contract
-----------------------

First, load the smart contract source code:

.. literalinclude:: ../src/djwebdapp_example/tezos/load.py
  :language: Python

Let's deploy our smart contract and call the ``mint()`` entrypoint by pasting the
following in our python shell started above, which you need to start if
you haven't already to run the following commands:

.. literalinclude:: ../src/djwebdapp_example/tezos/deploy.py
  :language: Python

This should store the deployed contract address in the address variable, copy
it or leave the shell open because you need it to index the contract in the
next section.

Indexing a contract
-------------------

Now that we have setup ``djwebdapp`` for a local tezos node, let's index a
contract, also programatically in ``./manage.py shell``:

.. literalinclude:: ../src/djwebdapp_example/tezos/index.py
  :language: Python

Normalizing incomming data: Models
----------------------------------

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
-----------------------------------

Finally, to connect the dots, we are first going to connect a custom callback
to ``djwebdapp_tezos.models.TezosTransaction``'s ``post_save`` signal to
create normalized ``Mint`` objects for every ``mint()`` call we index:

.. literalinclude:: ../src/djwebdapp_example/tezos/mint_normalize.py
  :language: Python

We are now ready to normalize the smart contract we have indexed:

.. literalinclude:: ../src/djwebdapp_example/tezos/normalize.py
  :language: Python

Deploy a contract
-----------------

.. literalinclude:: ../src/djwebdapp_example/tezos/deploy_contract.py
  :language: Python


Indexing contracts
==================

Example contract
----------------

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
   pymich compile FA12.py > FA12.tz

Local tezos blockchain
----------------------

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
-----------------------

First, load the smart contract source code:

.. literalinclude:: ../src/djwebdapp_example/tezos/load.py
  :language: Python

Let's deploy our smart contract and call the ``mint()`` entrypoint by pasting the
following in our pytezos python shell started above, which you need to start if
you haven't already to run the following commands:

.. literalinclude:: ../src/djwebdapp_example/tezos/deploy.py
  :language: Python

This should store the deployed contract address in the address variable, copy
it or leave the shell open because you need it to index the contract in the
next section.

Setting up a blockchain network
-------------------------------

Now that we have deployed a contract, let's setup ``djwebdapp`` for a local
tezos node, also programatically in ``./manage.py shell``:

.. literalinclude:: ../src/djwebdapp_example/tezos/blockchain.py
  :language: Python

Indexing a contract
-------------------

Now that we have deployed a contract, and setup ``djwebdapp`` for a local tezos
node, let's index a contract, also programatically in ``./manage.py shell``:

.. literalinclude:: ../src/djwebdapp_example/tezos/index.py
  :language: Python

Indexing a contract with a lot of history
-----------------------------------------

This process is very slow to index a smart contract that was deployed say 200k
blocks ago. To acheive this, we can use the tzkt API on tezos as such:

.. code-block:: python

    blockchain.provider.download(your_contract_address)

You can also use the ``./manage.py history_download`` command.

Normalizing incomming data: Models
----------------------------------

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
happen on the blockchain such as ``mint()``, ``transfer()`` or ``burn()`` calls.

In this case, you should subclass :py:class:`Normalizer` into a new
:py:class:`~djwebdapp_fa2.normalizers.Fa2Normalizer` class that you'd declare
in your app's ``normalizers`` module, in our case ``djwebdapp_fa2.normalizers``, so
that it's automatically discovered by ``djwebdapp`` which will attempt to import
the ``normalizers`` module of each installed app.

Then, all you have to do is add ``normalizer_class`` attribute to your Model
class, in our case ``normalizer_class = "Fa2Normalizer"``, this maps the
``Fa2Contract`` method calls to ``Fa2Normalizer``.

Then, call :py:meth:`djwebdapp.provider.Provider.normalize()` method, ie. as
``blockchain.provider.normalize()`` or the ``./manage.py normalize`` command
which you can run in a bash while loop.

We have created example models in the ``src/djwebdapp_fa2`` directory:

.. literalinclude:: ../src/djwebdapp_fa2/models.py
  :language: Python

And an example ``normalizers.py``;

.. literalinclude:: ../src/djwebdapp_fa2/normalizers.py
  :language: Python

Vault
=====

Setup
-----

Make sure you have installed djwebdapp with the ``[vault]`` dependencies (or
``[all]``).

.. note:: You may rotate Fernet keys used for encryption, please refer to
          `djfernet
          <https://djfernet.readthedocs.io/en/latest/#keys>`_
          documentation.

Importing a wallet
------------------

.. literalinclude:: ../src/djwebdapp_example/tezos/wallet_import.py
  :language: Python

Creating a wallet
-----------------

.. literalinclude:: ../src/djwebdapp_example/wallet_create.py
  :language: Python

Transfering coins
-----------------

.. literalinclude:: ../src/djwebdapp_example/tezos/transfer.py
  :language: Python

Refreshing balances
-------------------

.. literalinclude:: ../src/djwebdapp_example/balance.py
  :language: Python

Deploy a smart contract
-----------------------

.. literalinclude:: ../src/djwebdapp_example/tezos/deploy_contract.py
  :language: Python

API
===

Models
------

.. automodule:: djwebdapp_tezos.models
   :members:

Provider
--------

.. automodule:: djwebdapp_tezos.provider
   :members:
