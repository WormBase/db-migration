=========
AWS Setup
=========
The commands here will setup the AWS client for access to the WormBase
AWS account, for the purpose of running the migration.

.. attention:: 

   The commands below should be run on the :term:`EC2` host that will
   be used to perform the migration.


Installation requirements
=========================

Python_ is the only requirement.


Python package management
-------------------------
pip3_ is used to manage Python packages.

The ``--user`` flag instructs pip to install packages in your home
directory.

The installation locations for all Python packages when using the
``--user`` flag are:

Linux
  ``${HOME}/.local``

Mac OSX
  ``${HOME}/Library``


:term:`AWS` :term:`CLI` and :term:`azanium` Installation
========================================================
Below, `$AZANIUM_WHEEL_URL` should be the url of the wheel_ file
(`.whl` extension) listed in the downloads section of this
repository's `latest release page`_.

.. code-block:: bash

   # Ensure to install the latest aws cli:
   pip3 install --user "awscli==1.15.36"
   # To install the latest version of the db migration code:
   pip3 install --user "$AZANIUM_WHEEL_URL"


.. _aws-client-configuration:

:term:`AWS` Configuration
=========================

A WormBase AWS administrator should have previously supplied
you with the required credentials:

  AWS_PROFILE
  	WormBase AWS IAM username (current session)

  AWS_DEFAULT_PROFILE
  	WormBase AWS IAM username (all sessions)

  AWS_DEFAULT_REGION
  	The default region of the WormBase AWS account (Always `us-east-1`)

  AWS_ACCESS_KEY_ID
  	Secret generated within the AWS IAM console

  AWS_SECRET_ACCESS_KEY
  	Secret key generated within the AWS IAM console

The `aws configure` below will ask for a default ``region``, you
should specify `us-east-1` (this the primary `AWS region`_ that the
WormBase services are operated from).

These credentials should be given as input to the following command:

.. code-block:: bash

   aws configure --profile="${AWS_USER}"


Next, you should modify the file:

  `~/.aws/config`

and add the following profile as shown below, substituting `$AWS_USER` for
the actual profile name used in the `aws configure` command above:

.. code-block:: ini

   [profile wb-db-migrator]
   region = us-east-1
   role_session_name = wb-db-migrator
   role_arn = arn:aws:iam::357210185381:role/wb-db-migrator
   source_profile = $AWS_USER


Environment limitations
=======================
The :term:`client commands` used to interact with :term:`AWS` expects
that all `azanium admin` commands to be invoked from the same working
directory, from the same computer the initial commands are run from.

If for some reason, its desired to run this command from a different machine,
the following files must be copied (in addition to installing the software):

  .. code-block:: text

	~/.db-migration.db
	~/.azanium.conf
	~/.aws/credentials
	~/.aws/config


.. note:: The above assumes you've run all commands from your `$HOME` directory.

.. _Python: https://www.python.org/downloads/
.. _pip3: https://en.wikipedia.org/wiki/Pip_(package_manager)
.. _`AWS region`: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html
.. _`latest release page`: https://github.com/Wormbase/db-migration/releases/latest
.. _wheel: http://pythonwheels.com/
