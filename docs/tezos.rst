djWebdApp Tezos
~~~~~~~~~~~~~~~

Example contract
================

We will need to instanciate a contract on this blockchain. We'll use a simple
example in actually pure Python with the PyMich compiler.

We have an ``example.py`` contract source code and its compiled version in an
``example.json`` file in ``src/djwebdapp_tezos``. This is what the Python code
is like:

.. literalinclude:: ../src/djwebdapp_tezos/example.py
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

We provide a ``docker-compose.yml`` in the ``src/djwebdapp_tezos`` directory of
this repository, get in there and run ``docker-compose up``.

As some of us will also want to convert this to `GitLab-CI
services <https://docs.gitlab.com/ee/ci/services/>`_\ , we'll refer to our services
by hostname from now on, which is why we add the following to
``/etc/hosts``\ :

.. code-block::

   127.0.0.1 tzlocal api

You should then have:

* a local tezos sandbox on ``tzlocal:8732`` which autobakes every second (like
  geth development mode)
* a local tzkt API on ``api:5000``

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

.. code-block:: py

   import json, time
   from pytezos import pytezos
   from pytezos.operation.result import OperationResult
   client = pytezos.using(
       key='edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh',
       shell='http://tzlocal:8732',
   )
   source = json.load(open('src/djwebdapp_tezos/example.json'))
   storage = {'prim': 'Pair', 'args': [[], {'int': '0'}, {'string': 'tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx'}]}
   operation = client.origination(dict(code=source, storage=storage)).autofill().sign().inject(_async=False)
   time.sleep(2)  # wait for sandbox to bake
   opg = client.shell.blocks[operation['branch']:].find_operation(operation['hash'])
   res = OperationResult.from_operation_group(opg)
   address = res[0].originated_contracts[0]
   client.contract(address).mint('tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx', 1000).send().autofill().sign().inject()
   print('CONTRACT ADDRESS: ' + address)

This should output the deployed contract address, in my case
``KT1HPBnfPPkbUzNvW9HBKM4tTzBciVeswCR4`` which I'll refer to from now on.

Indexing a contract
===================

Now that we have deployed a contract, and setup ``djwebdapp`` for a local tezos
node, let's index a contract, also programatically so in ``./manage.py shell``:

.. code-block:: py

   from djwebdapp.models import Blockchain, SmartContract

   # First, we need to add a blockchain in the database
   blockchain, _ = Blockchain.objects.get_or_create(
       name='Tezos Local',
       provider_class='djwebdapp_tezos.provider.TezosProvider',
       configuration=dict(
           tzkt='http://api:5000',
       ),
   )

   # Then, insert a smart contract with our address
   contract, _ = SmartContract.objects.get_or_create(
       blockchain=blockchain,
       address='KT1Kie724z2jXbbm9AnTaNYsRJeAbax88Hqb',
   )

   contract.sync()

   print(contract.call_set.first().__dict__)

This will synchronize the contract using the tzkt API.

.. note:: Instead of the above code, we could have added the Blockchain and
          SmartContract in the admin and called ``./manage.py
          index_contracts``.

Normalizing incomming data
==========================

In the ``djwebdapp_tezos_demo`` app we have created some sample models to
normalize incomming data, if you want to create your own in your own project
this completely arbitrary code that would go in the ``models.py`` script in a
new app you would have created with ``./manage.py startapp``.

You can see the example source code in question in ``djwebdapp_demo/models.py``,
it registers 2 callbacks:


* ``call_mint``: is connected to the standard django post_save signal for the
  Call model,
* ``balance_update``: is connected to the ``djwebdapp.signals.contract_indexed``
  signal.

.. code-block:: py

   from djwebdapp.models import SmartContract

   contract.fa12
   # <FA12: KT1Kie724z2jXbbm9AnTaNYsRJeAbax88Hqb>

   contract.fa12.mint_set.all()
   # <QuerySet [<Mint: mint(tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx, 1000)>]>

   from djwebdapp_tezos_demo.models import Balance

   Balance.objects.all()
   # <QuerySet [<Balance: tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx balance: 1000>]>

Writing the blockchain
======================

To write the blockchain, you will need to add a node to your blockchain and then
Add
``djtezos_vault`` to your ``INSTALLED_APPS`` settings and run ``./manage.py migrate``.

Then, create a new wallet in a blockchain:

.. code-block:: py

   from djwebdapp.models import Blockchain
   from djwebdapp_vault.models import Wallet


   wallet = Wallet.objects.create(
   )
