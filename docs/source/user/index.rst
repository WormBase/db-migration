.. _db-migration-steps:

============================
Database Migration Procedure
============================
:term:`azanium`, the migration software is a Python package, which
will be used for running all migration commands.  All commands are all
required to be invoked from the same working directory, and from the
same host machine.

The sections below will need to be repeated for each migration run.

Software Setup
==============
Install via the URL: `$AZANIUM_WHEEL_URL`.
This URL can be obtained by copying the link with the `.whl` extension,
listed under the section "Assets" on `latest release page`_.

.. code-block:: bash

   python3 -m pip install --user --upgrade pip
   pip3 install --user "$AZANIUM_WHEEL_URL"

Verify installation has succeeded this by using the `--help` command:

.. code-block:: bash

   azanium --help


Configuration
=============
For each migration run, the software needs to be configured with the
FTP URL pointing to the data release:

.. code-block:: bash

   azanium configure $FTP_URL $RELEASE_TAG

Enabling Slack notifications
----------------------------

.. note::

   The configuration of the slack URL need only be done once, and will
   persist across migration runs.

Migration steps can optionally broadcast messages to a WormBase slack
channel to inform interested parties about the progress of the
migration.

To enable slack notifications to the `#db-migration-events` channel
in the WormBase slack, specify the `$WEBHOOK_URL` as the value for
`--slack-url` option to the configure command.

The value for `$WEBHOOK_URL` is available from the WormBase
slack management console for the WormBase organisation.

.. important::

   To obtain the Webhook URL using the following instructions, you
   must be logged in as an administrator to the WormBase Slack

To find the Webhook URL:
   1. Visit the `Slack API Apps page` (must be logged in as a manager)
   2. Click the active "azanium" application  listed under "Your Apps"
   3. Click "Incoming Webhooks" under "Features" (left side-menu)
   4. In the listing of Webhook URLs, click the top-most (latest)
      Webhook URL, listed against the `#db-migration-events` channel.

An example of configuring the Slack Webhook URL in conjunction with
the `$FTP_URL` required to specify the release:


.. code-block:: bash

   azanium configure $FTP_URL --slack-url=$WEBHOOK_URL

Commands
========
The following steps below will migrate the ACeDB database to Datomic.

The end result will be a Datomic database, compressed as an archive on
the host the migration is performed upon.

The location of the file should be:
   /wormbase/datomic-db-backups/<RELEASE>.tar.xz


1. Connect via ssh to the machine where you'll run the migration commands

   Use either a `screen` or `tmux` session, e.g:

   .. code-block:: bash

      tmux new-session -s azanium-commands

   Clean up after any previous migration:

   .. code-block:: bash

      azanium clean-previous-state

2. Install software

   .. code-block:: bash

      azanium install

3. Run the main migration

   .. code-block:: bash

      azanium migrate

   This command will execute all the steps required to perform the migration:

   1. Extract all .ace files from the ACeDB database for the current release.
   2. Compress all .ace files
   3. Create the Datomic database
   4. Convert .ace files to EDN logs
   5. Sort all EDN logs by timestamp
   6. Import the EDN logs into the Datomic database
   7. Run a QA report on the database
   8. Backup the Datomic database

 4. Run the homology migration

   Ensure there is enough memory to perform this step.
   The easiest way to ensure this is to reboot the instance before
   running the command for this step.

   .. code-block:: bash

      azanium migrate-homol

   1. Create a homology database
   2. Backup the homology database.

 5. Notify watchers of completion of the process.

   1. Notify watchers of the slack channel that the migration has completed.

      If slack integration was configured, you can use (e.g):

      .. code-block:: bash

	 azanium notify \
	     "Migration of ACeDB WS254 to Datomic complete! :fireworks:"

      Otherwise, write a message manually to the `#db-migration-events` slack channel.


Resulting Products
==================
The followings files are created by the migration:

   Datomic Database:

      /wormbase/datomic-db-backup/*/$WS_RELEASE.tar.xz

   QA Report

      /wormbase/$WS_RELEASE-report.csv

   Log file:

      /wormbase/logs/azanium.log


Other Resources
---------------

  Datomic transactor logs directory:

  	/wormbase/datomic_free/log

  circus log file (`circus` is the hypervisor for running the transactor):

  	/wormbase/circus-datomic-transactor.log


Other commands
--------------
The following *may* be useful when manual intervention is required.

Reset the migration to a step (prompts):

  .. code-block:: bash

     azanium reset-to-step

  Manually restart the transactor:

  .. code-block:: bash

     circusctl restart datomic-transactor


.. _`latest release page`: https://github.com/Wormbase/db-migration/releases/latest
.. _`Slack API Apps page`: https://api.slack.com/apps
