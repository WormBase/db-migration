.. notifications:

=============
Notifications
=============
The database migration processes will send notifications to a
dedicated :term:`Slack` channel:

  `#wb-db-migration-events`

.. note:: Notification support requires access to the WormBase DB
          Development slack group

As a user performing database migration, you should have received an
invitation, or otherwise subscribed to this channel.

Notifications are sent before and after each build step; at the end of
the process a notification will sent to confirm the migrated Datomic
databases’ location on Amazon :term:`S3` storage To configure
notifications for you and the WormBase team:

Enter the `slack webhook url`_ into a file in your home directory,
named as follows:

 `~/.azanium.conf`

The format of the file should match the following:

.. code-block:: ini

   [azanium.notifications]
   url = https://hooks.slack.com/services/<UNIQUE_TOKEN_1>/<UNIQUE_TOKEN_2>


.. _`slack webhook url`: https://wormbase-db-dev.slack.com/services/B1HNK2JEM#service_setup
