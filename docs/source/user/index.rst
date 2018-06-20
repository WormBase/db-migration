.. _db-migration-steps:

============================
Database Migration Procedure
============================
All :term:`azanium` migration commands are all required to be invoked from the
same working directory, and from the same host machine.

Software Setup
==============
The migration software is a Python package (:term:`azanium`).
This will be used for running all migration commmands.
Copy the `$AZANIUM_WHEEL_URL` url (The link listed with the `.whl`
extension) listed in the downloads section of this repository's
`latest release page`_.

.. code-block:: bash

   python3 -m pip install --user --upgrade pip
   pip3 install --user "$AZANIUM_WHEEL_URL"


Configuration
=============
Each time the migration is run, it's required to configure the migration
with the FTP URL of the release.

.. code-block:: bash

   azanium configure $FTP_URL


Enabling Slack notifications
----------------------------
To enable slack notifications of each build step to the
`#db-migratione-events` channel in the WormBase slack, specify the
`$WEBHOOK_URL` as the value for `--slack-url` option to the configure
command.  The value for `$WEBHOOK_URL` is available from the WormBase
slack management console for the WormBase organisation.

To find the Webhook URL:
   1. Visit https://api.slack.com/apps
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
Then end result will be a Datomic database, compressed as an arhive on
the host the migration is performed.

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

3. Run the migration

   .. code-block:: bash

      azanium migrate-stage-1

   This command will execute steps for stage 1 of the migration:

   1. Extract all .ace files from the ACeDB database for the current release.
   2. Compress all .ace files
   3. Convert .ace files to EDN logs
   4. Sort all EDN logs by timestamp


   .. attention::

      restart the instance to free-up resources on the host (memory).

   Continue the migration (Stage 2):

   .. code-block:: bash

      azanium migrate-stage-2

   This command executes the remaining steps required to complete the migration.

   5. Create the Datomic database
   6. Import the EDN logs into the Datomic database
   7. Run a QA report on the database

      .. note:: Once this step has completed, the user will be prompted
	        in the tmux/screen shell session to confirm the next step, or abort.
	        This will also be posted to the slack channel for
	        tracking migration events (if notifications are enabled).

   8. Backup the Datomic database

   9. Write migration procedure completion notification to the #db-migration-events
       wormbase-db-dev slack channel.

       .. code-block:: bash

          azanium notify \
	     "Migration of ACeDB WS254 to Datomic complete! :fireworks:"


Resulting Products
==================
The followings files are created by the migration:

   Datomic Database:

      /wormbase/datomic-db-backups/$WS_RELEASE.tar.xz

   QA Report

      /wormbase/$WS_RELEASE-report.csv

   Log file:

      /wormbase/logs/azanium.log



.. _`latest release page`: https://github.com/Wormbase/db-migration/releases/latest
