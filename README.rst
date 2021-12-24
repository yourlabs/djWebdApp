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

To install djwebdapp with all optional dependencies:

```
pip install djwebdapp[all]
```

See setup.py's extra_requires for other possibilities.

Demo project
------------

For this tutorial, we'll use the ``djwebdapp_demo`` project:

* clone this project and go into the repository clone directory
* run ``pip install -e .[all]``
* run ``./manage.py migrate``
* run ``./manage.py createsuperuser``
* run ``./manage.py runserver`` to start a server on http://localhost:8000/admin
* run ``./manage.py shell`` to run Python commands

Custom project
--------------

Instead of the demo project, you can also create your own project, instead of
the first step of cloning do:

* run ``django-admin startproject your_project_name``
* in ``your_project_name/your_project_name/settings.py``, add ``djwebdapp`` to
  ``INSTALLED_APPS``,
* proceed with the next steps ``migrate`, ``createsuperuser``, ``runserver``
  ...

Tutorial
--------

Read documentation `online
<https://djwebdapp.rtfd.io>`_ or in the ``docs/`` directory.
