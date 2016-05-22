==============================
 Hacking on the db-build tool
==============================

System requirements
===================
This code was developed against Python3.5 on ubuntu, and has been verified
to work with Python3.4 on Amazon Linux (AWS AMI).

Development
===========

Setup
-----
We use virtualenv_ for developing;
If you're using a version of Python <= 3.4 on Linux provided by the
system package manager, you'll need to install an extra package:

.. code-block:: bash

   # The following is for Ubuntu/Debian systems, you may need an
   # equivilent package for RedHat/Fedora/CentOS
   sudo apt-get install python3-venv


Create a virtualenv:

.. code-block:: bash

   VENV_HOME="~/.virtualenv"
   mkdir -p "${VENV_HOME}"
   VENV="${VENV_HOME}/wormbase-db-build"
   python3 -m venv "${VENV}"
   # Activate the virtualenv (type deactivate to return to normal shell)
   source "${VENV}/bin/activate"


Coding style
============
The code in this project is QA'd using the flake8_ tool,
which is to say it mostly follows the `standard Python coding style`_.

Errors which are turned off are set in setup.cfg at the project root.

Run code QA with the following:

.. code-block:: bash

   flake8 src


Manual testing
==============
Within an active virtualenv:

.. code-block:: bash

   # All the following commands are intended to be run from the project root.
   rebuild='pip uninstall -y wormbase-db-build && \
	    rm -rf ./dist ./build && \
	    python setup.py sdist && \
	    pip install \
            dist/wormbase-db-build-0.1.tar.gz'
   rebuild
   # run a command line tool command to test any change, for example:
   wb-db-install pseudoace 0.4.4


Documentation
=============
Is written in reStructuredText_ as is common in most Python projects.


.. _virtualenv: http://docs.python-guide.org/en/latest/dev/virtualenvs/
.. _reStructuredText: http://www.sphinx-doc.org/en/stable/rest.html
.. _flake8: http://flake8.readthedocs.io/en/latest/config.html
.. _`standard Python coding style`: https://www.python.org/dev/peps/pep-0008/


