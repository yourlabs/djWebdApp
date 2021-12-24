djWebdApp Project
~~~~~~~~~~~~~~~~~

You may use the demo project or create your own and install djwebdapp there.

Django basics
=============

If you are not familiar with the Django development framework, it is
recommended you follow `their tutorial first
<https://docs.djangoproject.com/en/4.0/intro/tutorial01/>`_, even though you
can go through this tutorial copy/pasting your way.

Demo project
============

For this tutorial, we'll use the ``djwebdapp_demo`` project:

* clone this project and go into the repository clone directory
* run ``pip install -e .[all]``
* run ``./manage.py migrate``
* run ``./manage.py createsuperuser``
* run ``./manage.py runserver`` to start a server on http://localhost:8000/admin
* run ``./manage.py shell`` to run Python commands

Custom project
==============

Instead of the demo project, you can also create your own project, instead of
the first step of cloning do:

* run ``django-admin startproject your_project_name``
* in ``your_project_name/your_project_name/settings.py``, add ``djwebdapp`` to
  ``INSTALLED_APPS``,
* proceed with the next steps ``migrate`, ``createsuperuser``, ``runserver``
  ...
