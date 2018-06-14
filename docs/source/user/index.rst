.. _db-migration-user-guide:

.. toctree::
   :hidden:
   :maxdepth: 1

   guide

============================
Database Migration Procedure
============================
The database migration can be performed on any host.
Currently, it is performed on an :term:`EC2` instance.
Upon successful completion, the following files will be available on the host
used to run the migration commands:

   Datomic Database:

      /wormbase/datomic-db-backups/$WS_RELEASE.tar.xz

   QA Report

      /wormbase/$WS_RELEASE-report.csv

   Log file:

      /wormbase/logs/azanium.log

The migration process usually takes approximately 3½ days to complete.
There is currently a memory issue which necessitates splitting up the migration
procedure into two stages.

`<Notifications :ref:`Notifications`> can be sent before and after each step of
the migration process, assuming the migration user configures notifications (A one-time task).

