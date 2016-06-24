============================
Database Migration Procedure
============================
The database migration will be performed on an ephemeral :term:`EC2`
instance.  Upon successful completion, the migrated Datomic database
will be stored in :term:`S3` storage.

The migration process will take approximately 3½ days to complete.

`Notications <notications>` will be sent before and after each step of
the migration process.

*Any* person having a WormBase Amazon :term:`AWS` account will be
 capable of performing the migration procedure.

Prerequisites
-------------

  * A WormBase AWS “IAM” account

    An AWS administrator will need to have previously supplied
    the following required credentials:

  	*aws-username*

	*AWS_ACCESS_KEY_ID*

  	*AWS_SECRET_ACCESS_KEY*

  * Python 3.4+

    On a unix-like machine, check the version with:

    .. code-block:: bash

       $ which python3 && python3 -V

.. notifications:

Notifications
-------------
The database migration processes will send notifications to the
`#wb-db-migration-events` channel on the wormbase-db-dev :term:`slack`
channel.

Notifications are sent before and after each build step; at the end of
the process a notification will sent to confirm the migrated Datomic
databases’ location on Amazon :term:`S3` storage To configure
notifications for you and the WormBase team:

Enter the `SLACK_WEBHOOK_URL` to the following command (This can be
found here)

.. code-block:: bash

   azanium configure <SLACK_WEBHOOK_URL>


.. toctree::
   :hidden:
   :maxdepth: 1

   setup
   commands
