================
Build user setup
================

Installation
============

System Requirements
-------------------

Python3.4 (yum based systems)
-----------------------------

.. code-block:: bash

   sudo yum install -y
		libffi-devel \
		openssl-devel \
		readline-devel \
		python34 \
		python34-pip \
		python34-tools \
		python34-libs \
		python34-virtualenv

Python3 (ubuntu)
----------------

.. code-block:: bash

   sudo apt-get install -y \
		libffi-dev \
		libssl-dev \
		libreadline-dev \
		python3-dev \
		python3-pip \
		python3-venv


Install
=======

.. note:: The following would change to download a binary from github
	  If the db-build repository could be made public, the following
	  installation procedure could simplified to `pip install tarball-url`.


.. code-block:: bash

   git clone <this-repo>
   python3 -m pip install --user virtualenv
   mkdir -p ~/.virtualenvs
   virtualenv -p python3 ~/.virtualenvs/db-build
   git checkout <tag>
   python setup.py sdist
   pip install dist/wormbase-db-build-<tag>.tar.gz



Useful extras
-------------
  * The `Java EC2 command line tools`_ (Useful for decoding error messages)


.. _`download Python`: https://www.python.org/downloads/
.. _`Java EC2 command line tools`: http://docs.aws.amazon.com/AWSEC2/latest/CommandLineReference/set-up-ec2-cli-linux.html
