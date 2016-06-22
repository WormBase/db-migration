=======
Testing
=======

Bootstrapping an EC2 instance
=============================
The code in this package is used both locally (wrapping AWS client
commands), and on the EC2 instance (Running commands).

The installation procedure "bootstraps" the instance with a distribution
of this package.

When manually testing, please pass the ``--dev-mode`` flag to
``azanium cloud`` command, e.g:

.. code-block:: bash

   azanium cloud init --dev-mode WS254

This will bootstrap the instance with the code from your local working
directory.

Without the ``dev-mode`` flag, the latest release on github will be
used to bootstrap the instance.


.. _virtualenv: http://docs.python-guide.org/en/latest/dev/virtualenvs/
