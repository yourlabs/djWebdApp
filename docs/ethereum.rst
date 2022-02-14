djWebdApp Ethereum
~~~~~~~~~~~~~~~~~~

Indexing contracts
==================

Example contract
----------------

We will need to instanciate a contract on this blockchain. We'll use a simple
example smart contract in solidity that looks like some FA12:

.. literalinclude:: ../src/djwebdapp_example/ethereum/FA12.sol
  :language: Solidity

We already compiled it, but you can change it and recompile it with the
following command:

.. code-block:: sh

    cd src/djwebdapp_example/ethereum
    solc --abi --overwrite --output-dir . --bin FA12.sol

Example contract deployment
---------------------------

.. danger:: Before you begin, make sure you have followed the setup
            instructions from :ref:`Local blockchains`.

With the Ethereum sandbox, we'll use the default account which is already
provisionned with some ethers.

Let's deploy our example contract using `Web3py
<https://web3py.readthedocs.io>`_, install it and start a Python shell with the
``./manage.py shell`` command at the root of our repository:

.. code-block:: sh

   pip install web3
   ./manage.py shell

.. note:: The above example also works in a normal Python shell started with
          the ``python`` command, but we need to be in the Django shell of the
          demo project to go through this tutorial anyway.

In the shell, make sure your default account is provisionned properly:

.. literalinclude:: ../src/djwebdapp_example/ethereum/client.py
  :language: Python

Check your client balance:

.. code-block:: python

    >>> w3.eth.default_account
    '0xD1562e5128FC95311E46129a9f445402278e7751'
    >>> w3.eth.get_balance(w3.eth.default_account)
    115792089237316195423570985008687907853269984665640564039457577993160770347781

Deploy a smart contract
-----------------------

First, load the smart contract source code:

.. literalinclude:: ../src/djwebdapp_example/ethereum/load.py
  :language: Python

Let's deploy our smart contract and call the ``mint()`` entrypoint by pasting the
following in our python shell started above, which you need to start if
you haven't already to run the following commands:

.. literalinclude:: ../src/djwebdapp_example/ethereum/deploy.py
  :language: Python

This should store the deployed contract address in the address variable, copy
it or leave the shell open because you need it to index the contract in the
next section.

Setting up a blockchain network
-------------------------------

Now that we have deployed a contract, let's setup ``djwebdapp`` for a local
ethereum node, also programatically in ``./manage.py shell``:

.. literalinclude:: ../src/djwebdapp_example/ethereum/blockchain.py
  :language: Python

Indexing a contract
-------------------

Now that we have setup ``djwebdapp`` for a local ethereum node, let's index a
contract, also programatically in ``./manage.py shell``:

.. literalinclude:: ../src/djwebdapp_example/ethereum/index.py
  :language: Python

Normalizing incomming data: Models
----------------------------------

We have created example models in the ``src/djwebdapp_example`` directory:

.. literalinclude:: ../src/djwebdapp_example/models.py
  :language: Python

.. note:: You wouldn't have to declare ForeignKeys to other Transaction classes
          than EthereumTransactions, but we'll learn to do inter-blockchain
          mirroring later in this tutorial, so that's why we have relations to
          both.

And declared a function to update the balance of an FA12 contract:

.. literalinclude:: ../src/djwebdapp_example/balance_update.py
  :language: Python

Normalizing incomming data: Signals
-----------------------------------

Finally, to connect the dots, we are first going to connect a custom callback
to ``djwebdapp_ethereum.models.EthereumTransaction``'s ``post_save`` signal to
create normalized ``Mint`` objects for every ``mint()`` call we index:

.. literalinclude:: ../src/djwebdapp_example/ethereum/mint_normalize.py
  :language: Python

We are now ready to normalize the smart contract we have indexed:

.. literalinclude:: ../src/djwebdapp_example/ethereum/normalize.py
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

.. literalinclude:: ../src/djwebdapp_example/ethereum/wallet_import.py
  :language: Python

Creating a wallet
-----------------

.. literalinclude:: ../src/djwebdapp_example/wallet_create.py
  :language: Python

Transfering coins
-----------------

.. literalinclude:: ../src/djwebdapp_example/ethereum/transfer.py
  :language: Python

Refreshing balances
-------------------

.. literalinclude:: ../src/djwebdapp_example/balance.py
  :language: Python

Deploy a contract
-----------------

.. literalinclude:: ../src/djwebdapp_example/ethereum/deploy_contract.py
  :language: Python
