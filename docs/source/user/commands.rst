.. _db-migration-steps:

========
Commands
========
The following steps below will migrate the ACeDB database to Datomic.
Then end result will be a Datomic database stored on Amazon :term:`S3`,
which can be restored using any recent version of :term:`Datomic`.

.. note:: You must have ``ssh-agent`` running in your shell session.

.. _db-migration-step-1:

1. **Provision and bootstrap an EC2 instance**

   The following :term:`azanium` sub-command below will
   print out the ssh commands needed for the next step.

   .. code-block:: bash

      AWS_PROFILE="${USER}"
      WB_DATA_RELEASE="WS254"
      azanium cloud --profile "${USER}" init "${WB_DATA_RELEASE}"

.. _db-migration-step-2:

2. **Connect to the EC2 instance using ssh - run the migrate command**

   The commands below will emit their current progress to the console,
   and will also print out the location of a log file for more detailed
   output.


   Use the `ssh` command printed from step 1 to connect to the EC2 instance.

   .. note:: You may need to add the identity to ``ssh-agent`` first.

      .. code-block:: bash

   	ssh-add ~/.ssh/wb-db-migrate.pem

   Then, using either `screen` or `tmux` session, e.g:

   .. code-block:: bash

      tmux new-session -s azanium-commands

   issue the following command:

   .. code-block:: bash

      azanium migrate

   This command will execute each step of the build:

   1. Extract all .ace files from the ACeDB databsae for the current release.
   2. Compress all .ace files
   3. Convert .ace files to EDN logs
   4. Sort all EDN logs by timestamp
   5. Create the Datomic datbase
   6. Import the EDN logs into the Datomic database
   7. Run a QA report on the database

      .. note:: Once this step has completed, the user is prompted to
         	confirm the next step, or abort.

   8. Transfer the Datomic database to Amazon S3 storage


.. _db-migration-step-3:

3. **Terminate the EC2 instance**

   .. code-block:: bash

      azanium cloud --profile $USER terminate


Should all steps complete successfully, the migration process is now
complete.

If you stopped after :ref:`Step 2 <db-migration-step-2>` due to data
inconsistency, or an error occurred during any of the other steps,
please ensure to eventually run :ref:`Step 3 <db-migration-step-3>`.
