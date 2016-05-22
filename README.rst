============
aws-db-build
============

Provides command line interfaces (cli) for performing 
tasks to realise the Datomic database migration from ACeDB on AWS.

Each command is named ith a `wb-db-` prefix.

When installed as documented below, these tools should
have been automatically added to `$PATH`.


System requirements
===================
 * Python34+
 * Java version 8
 * readline developement libraies
   * libreadline.so.5 is needed for ACeDB "tace" binary.
 * 300GB of disk space in addition to O/S space requirements, preferably SSD storage.
   * (A total of 500GB should be plenty)
 * A minimum of 32Gb of RAM for running the full process.
 * The `Java EC2 command line tools`_ (Useful for decoding error messages)
 * The Python AWS command line client
   * Install with:
     .. code-block:: bash
	
	pip install --user awscli
		   
		   
Usage requirements
==================
You'll need:

  - An Amazon EC2 account, conifgured as per WormBase documentation.
  - TBD: IAM user and group setup documentation.


The `wb-db-aws` CLI provides tools for configuring your AWS IAM resources.

 
Installation
============

1. Install the Amazon command line interface

.. code-block:: bash

   # User site-packages only
   python -m pip install --user awscli

   # or install system-wide (name may vary), following is for Ubutnu linux
   sudo apt-get install -y awscli

2. TDB


Development
===========
See HACKING.rst


.. _`AWS cloud-config UserData template`: AWS-cloud-config-Userdata.template
... _`Java EC2 command line tools`: http://docs.aws.amazon.com/AWSEC2/latest/CommandLineReference/set-up-ec2-cli-linux.html

