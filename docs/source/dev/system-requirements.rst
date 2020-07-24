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

   sudo yum update -y
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
   sudo yum groupinstall -y "Development Tools"
   sudo update-alternatives --set java /usr/lib/jvm/jre-1.8.0-openjdk.x86_64/bin/java
   sudo wget http://repos.fedorapeople.org/repos/dchen/apache-maven/epel-apache-maven.repo -O /etc/yum.repos.d/epel-apache-maven.repo
   sudo sed -i s/\$releasever/6/g /etc/yum.repos.d/epel-apache-maven.repo
   sudo yum install -y apache-maven


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
                maven \
		openjdk-8-jdk-headless


TACE
----
The command line tool provided by the ACeDB software currently requires the
following hack to make it work on the Amazon instance used for the migration:

.. code-block:: bash

   #  Expects libreadline.so.5, which is not available for installation,
   #  but libreadline6 is, and works.
   sudo ln -s /lib64/libreadline.so.6 /lib64/libreadline.so.5
