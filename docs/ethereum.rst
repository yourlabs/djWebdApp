djWebdApp Ethereum
~~~~~~~~~~~~~~~~~~

.. danger:: Before you begin, make sure you have followed the setup
            instructions from :ref:`Local blockchains`.

Setup
=====

Smart contract
--------------

In this tutorial, we'll use a simple example smart contract in solidity that
looks like some FA12:

.. literalinclude:: ../src/djwebdapp_example_ethereum/contracts/FA12.sol
  :language: Solidity

We already compiled it, but you can change it and recompile it with the
following command:

.. code-block:: sh

    cd src/djwebdapp_example_ethereum/contracts
    solc --abi --overwrite --output-dir . --bin FA12.sol

What matters is that the contract `.abi` and `.bin` files have matching names
and are both present in the `ethereum` sub-directory of the Django app where
corresponding models are going to live.

Web3 client
-----------

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

.. literalinclude:: ../src/djwebdapp_example_ethereum/client.py
  :language: Python

Check your client balance:

.. code-block:: python

    >>> client.eth.default_account
    '0xD1562e5128FC95311E46129a9f445402278e7751'
    >>> client.eth.get_balance(w3.eth.default_account)
    115792089237316195423570985008687907853269984665640564039457577993160770347781

Blockchain
----------

Now that we're ready to stimulate the blockchain, let's setup ``djwebdapp`` for
a local ethereum node, also programatically in ``./manage.py shell``:

.. literalinclude:: ../src/djwebdapp_example_ethereum/blockchain.py
  :language: Python

Account
-------

.. note:: You may rotate Fernet keys used for encryption, please refer to
          `djfernet
          <https://djfernet.readthedocs.io/en/latest/#keys>`_
          documentation.

.. literalinclude:: ../src/djwebdapp_example_ethereum/account.py
  :language: Python

Models
======

Custom
------

Along with our smart contract, we're creating some models to normalize all the
data both ways: to deploy transactions, as well as to index them.

``FA12Ethereum``
    Subclass of
    :py:class:`~djwebdapp_ethereum.models.EthereumTransaction` and defines
    k:py:attr:`~djwebdapp_ethereum.models.EthereumContract.contract_file_name`
    as well as
    :py:attr:`~djwebdapp_ethereum.models.EthereumContract.normalizer_class`,
    which we'll define in the next chapter

``FA12MintEthereum``
    Subclass of
    :py:class:`~djwebdapp_ethereum.models.EthereumCall` and defines
    :py:attr:`~djwebdapp.models.Transaction.entrypoint`

Note that both models define a
:py:meth:`~djwebdapp.models.Transaction.get_args()` method to return the
arguments that the blockchain client should use when deploying.

.. literalinclude:: ../src/djwebdapp_example_ethereum/models.py
  :language: Python

Contract deployment
-------------------

Time to see the beauty of all this, to deploy this smart contract, and make a
bunch of mint calls through Django models!

.. literalinclude:: ../src/djwebdapp_example_ethereum/deploy_model.py
  :language: Python

Indexing and normalization
--------------------------

Indexing is the process of parsing data from the blockchain, normalization is
the process of transforming incomming data into structured relational data.

To map incomming blockchain data into models, we'll define a
:py:class:`~djwebdapp.normalizers.Normalizer` for that contract, in a
``normalizers.py`` file in the same app, and define a method par contract
function that will be called by the indexer to normalize the data into your
models:

.. literalinclude:: ../src/djwebdapp_example_ethereum/normalizers.py
  :language: Python

First, let's call a smart contract function from outside djwebdapp, it's
the call that we are going to index and normalize, then, run the indexer and
the normalizer.

.. literalinclude:: ../src/djwebdapp_example_ethereum/normalize.py
  :language: Python

Wallets
=======

Importing a wallet
------------------

.. literalinclude:: ../src/djwebdapp_example_ethereum/wallet_import.py
  :language: Python

Creating a wallet
-----------------

.. literalinclude:: ../src/djwebdapp_example/wallet_create.py
  :language: Python

Transfering coins
-----------------

.. literalinclude:: ../src/djwebdapp_example_ethereum/transfer.py
  :language: Python

Refreshing balances
-------------------

.. literalinclude:: ../src/djwebdapp_example/balance.py
  :language: Python

API
===

Models
------

.. automodule:: djwebdapp_ethereum.models
   :members:

Provider
--------

.. automodule:: djwebdapp_ethereum.provider
   :members:
