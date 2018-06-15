===================
System requirements
===================
This code was developed against Python3.5 on ubuntu, and has been
verified to work with Python3.4 on Amazon Linux (AWS AMI).


Install your system's  Development tool-chain:

  yum (Amazon AMI, RedHat, Centos)

    .. code-block:: bash

       sudo yum groupinstall -y "Development Tools"

  apt (Debian, Ubuntu, Mint)

    .. code-block:: bash

       sudo apt-get install -y build-essential

  MacOSX - xcode

     TBD


Packages
========
The following package list is for yum based systems (AWS linux, RedHat
et al), using Python 3.4:


Python3.4 (Amazon AMI)
----------------------

.. code-block:: bash

   sudo yum install -y
		libffi-devel \
  		openssl-devel \
		readline-devel \
		java-1.8.0-openjdk-headless \
		python34 \
		python34-pip \
		python34-tools \
		python34-libs \
		python34-virtualenv

Python3.5 (ubuntu)
------------------

.. code-block:: bash

   sudo apt-get install -y \
		libffi-dev \
		libssl-dev \
		libreadline-dev \
		python3-dev \
		python3-pip \
		python3-venv \
		openjdk-8-jdk-headless
