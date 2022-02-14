djWebdApp
~~~~~~~~~

`**Documentation**
<https://djwebdapp.rtfd.io>`_

Django is a great web application framework "for perfectionists with deadlines".

A dApp is an app running on the blockchain: a smart contract on which users can
call functions on.

This module provides blockchain support for Django, for reading and/or writing
the blockchain, with the following features usable independently:

* blockchain indexer
* private key vault
* blockchain writer
* blockchain data normalization
* multiple blockchain support (tezos & ethereum so far)
* inter-blockchain contract synchronisation
* metamask authentication backend (TBA)

In addition to these features, djWebdApp differenciates itself from indexers
like dipdup because it is extensible: it's just a module you add to your Django
project like any other Django App, in which you can add models, endpoints, and
have an admin interface for free, and so on, benefiting from the `vast Django
ecosystem of apps <https://djangopackages.org/>`_.

Video demos
===========

- `Tezos tutorial demo
  <https://www.youtube.com/watch?v=quSX-gJ6eow>`_
- `Ethereum tutorial demo
  <https://www.youtube.com/watch?v=oTjvnjB_8Tc>`_

Getting started
===============

Django basics
-------------

If you are not familiar with the Django development framework, it is
recommended you follow `their tutorial first
<https://docs.djangoproject.com/en/4.0/intro/tutorial01/>`_, even though you
can go through this tutorial copy/pasting your way.

You may use the demo project or create your own and install djwebdapp there.

Install
-------

To install djwebdapp with all optional dependencies::

    # Use --use-deprecated legacy-resolver untill dipdup upgrades dependencies
    pip install --use-deprecated legacy-resolver djwebdapp[all][binary]

Don't use ``[binary]`` right there if you prefer to install compiled python
packages from your system package manager.

See setup.py's extra_requires for other possibilities.

Demo project
------------

For this tutorial, we'll use the ``djwebdapp_demo`` project:

.. code-block:: bash

    git clone https://yourlabs.io/oss/djwebdapp.git
    cd djwebdapp
    pip install --use-deprecated legacy-resolver --editable .[all][binary]
    ./manage.py migrate
    ./manage.py shell

.. _Local blockchains:

Local blockchains
-----------------

Instead of using mainnets for development, we're going to use a local
blockchains, so that we can work completely locally.

We provide a ``docker-compose.yml`` in the root directory of this repository,
run ``docker-compose up`` to start it.

As some of us will also want to convert this to `GitLab-CI
services <https://docs.gitlab.com/ee/ci/services/>`_\ , we'll refer to our services
by hostname from now on, which is why we add the following to
``/etc/hosts``::

   127.0.0.1 tzlocal tzkt-api ethlocal

You should then have:

- a local ethereum HTTP RPC API on ``ethlocal:8545`` with a WebSocket on
  ``ethlocal:30303``,
- a local tezos sandbox on ``tzlocal:8732`` which autobakes every second,
  useable like geth development mode.
- a local tzkt indexer which is completely optionnal.

See documentation for **Example contract deployment** in each blockchain
specific documentation pages for more pointers.

Custom project
--------------

Instead of the demo project, you can also create your own project, instead of
the first step of cloning do:

* run ``django-admin startproject your_project_name``
* in ``your_project_name/your_project_name/settings.py``, add to
  ``INSTALLED_APPS``: ``'djwebdapp', 'djwebdapp_tezos',
  'djwebdapp_ethereum'``... See ``djwebdapp_demo/settings.py`` for other
  INSTALLED_APPS you can use
* proceed with the next steps ``migrate`, ``createsuperuser``, ``runserver``
  ...

Tutorial
--------

Read documentation `online
<https://djwebdapp.rtfd.io>`_ or in the ``docs/`` directory.
