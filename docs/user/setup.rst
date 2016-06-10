=====
Setup
=====

Installation requirements
=========================

Python 3.4+ is the only requirement.
To test if your system has this version or higher:

.. code-block:: bash

   python -V

If your system does not already contain Python >= 3.4, then please use
your operating system's package manager (e.g apt, yum, brew) to obtain
a suitable version, or download and install the latest version of
`Python 3`_ from the Python website.


Python package management
-------------------------
pip_ is used to manage Python packages.

The ``--user`` flag instructs pip to install pip in your home directory.

The installation locations for all Python packages when using the
``--user`` flag are:

Linux
  ``${HOME}/.local``

Mac OSX
  ``${HOME}/Library``


.. code-block:: bash

   python3 -m pip install --upgrade --user pip


:term:`AWS` :term:`CLI` Installation
====================================

.. code-block:: bash

   pip3 install --user awscli


:term:`AWS` Configuration
=========================
A WormBase AWS administrator should have previously supplied
you with the required credentials:

  AWS IAM username

  AWS_ACCESS_KEY_ID

  AWS_SECRET_ACCESS_KEY


The `aws configure` below will ask for a default ``region``, you
should specify `us-east-1` (this the primary `AWS region`_ that the
WormBase services are operated from).

These credentials should be given as input to the following command:

.. code-block:: bash

   aws configure --profile $USER


Environment limitations
=======================
The :term:`client commands` used to interact with :term:`AWS` must be
invoked from the same working directory, from the same computer the
initial commands are run from.

Advanced usage
==============
This database migration program stores the state of migration process
in the current working directory, in the file:

	``.db-migration.shelve``

In order to interact with commands that use the EC2 instance
provisioned by :ref:`the first migration step <db-migration-step-1>`,
this file must be copied to all computers from which you run commands.

.. _`Python 3`: https://www.python.org/downloads/
.. _pip: https://en.wikipedia.org/wiki/Pip_(package_manager)
.. _`AWS region`: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html
