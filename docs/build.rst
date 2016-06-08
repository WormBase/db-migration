===============
Build procedure
===============

Preface
=======

The :term:`client commands` used to interact with :term:`AWS` must be
invoked from the same working directory, from the same computer the
initial commands are run from.

This build program stores the state of build in the current working directory,
in a file named ``.db-build.shelve`` (A Python "shelve" file).


Pre-requisite: Configuring an AWS account
-----------------------------------------
A WormBase AWS administrator should have previously supplied
credentials:

  AWS IAM username

  AWS_ACCESS_KEY_ID

  AWS_SECRET_ACCESS_KEY



These credentials should be given as input to the following command:

.. code-block:: bash

   aws configure --profile $USER


The build consists of 3 main steps:

1. Provision and run an EC2 instance.

2. Run commands on the EC2 instance.

3. Terminate the EC2 instance


Command Reference
=================

wb-db-build
  Used to run commands from the client machine to the AWS EC2 instance.

wb-db-run
  Used to run commands on the AWS EC2 instance in order to perform build steps.


.. literalinclude:: build-steps
