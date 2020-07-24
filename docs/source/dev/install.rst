============
Installation
============

Setup
=====
We use virtualenv_ for developing;
If you're using a version of Python <= 3.4 on Linux provided by the
system package manager, you'll need to install an extra package:

.. code-block:: bash

   # The following is for Ubuntu/Debian systems, you may need an
   # equivilent package for RedHat/Fedora/CentOS
   sudo apt-get install python3-venv


.. note::

   You may find that virtualenvwrapper_ is a more convenient tool.

Create a virtualenv:

.. code-block:: bash

   VENV_HOME="$HOME/.virtualenv"
   mkdir -p "${VENV_HOME}"
   VENV="${VENV_HOME}/azanium"
   python3 -m venv "${VENV}"
   # Activate the virtualenv (type deactivate to return to normal shell)
   source "${VENV}/bin/activate"


Install the source code in "editable" mode.

.. note::

   This means that we don't have to re-install our package
   each time we make a change.

.. code-block:: bash

   pip install --editable ".[dev]"


.. _virtualenv: http://docs.python-guide.org/en/latest/dev/virtualenvs/
.. _virtualenvwrapper: https://virtualenvwrapper.readthedocs.io/en/latest/
