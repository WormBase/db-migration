=======
Testing
=======

Bootstrapping an EC2 instance
=============================
The code in this package is used both locally (wrapping AWS client
commands), and on the EC2 instance (Running commands).

The installation procedure "bootstraps" the instance with a distribution
of this package.

The following command pipeline simplifies this re-building process.

Within an active virtualenv_:

.. code-block:: bash

   # All the following commands are intended to be run from the project root.
   rebuild='pip uninstall -y azanium && \
	    rm -rf ./dist ./build && \
	    python setup.py sdist && \
	    pip install \
            dist/azanium-0.1.tar.gz'
   rebuild
   # run a command line tool command to test any change, for example:
   azanium install pseudoace 0.4.4

.. _virtualenv: http://docs.python-guide.org/en/latest/dev/virtualenvs/
