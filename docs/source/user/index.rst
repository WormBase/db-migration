============================
Database Migration Procedure
============================
The database migration will be performed on an :term:`EC2` instance.
Upon successful completion, the migrated Datomic database will be
stored in :term:`S3` storage.

The migration process will take approximately 3½ days to complete.

`Notications <notications>` will be sent before and after each step of
the migration process.

*Any* person having a WormBase Amazon :term:`AWS` account will be
 capable of performing the migration procedure.


.. toctree::
   :hidden:
   :maxdepth: 1

   prerequisites
   notifications
   commands
