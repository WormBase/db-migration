.. _db-migration-steps:

========
Commands
========
The following steps below will migrate the ACeDB database to Datomic.
Then end result will be a Datomic database stored on Amazon :term:`S3`,
which can be restored using any recent version of :term:`Datomic`.

.. note:: You must have ``ssh-agent`` running in your shell session.


.. _db-migration-step-1:

1. **Start the DB Migration EC2 instance**

   Assuming you have correctly setup AWS Command Line Interface, using
   the `db migration ec2 instance id` provided by a WormBase AWS
   Administrator, enter the following :term:`aws cli` command to start
   the migration instance:

   .. code-block:: bash

      AWS_PROFILE="${USER}"
      INSTANCE_ID="${INSTANCE_ID_PROVIDED_BY_WORMBASE_AWS_ADMIN}"
      aws --profile "${AWS_PROFILE}" \
		   ec2 start-instances --instance-ids "${INSTANCE_ID}"

.. _db-migration-step-2:

2. **Connect to the EC2 instance using ssh - run the migrate command**

   Use the following command check the status of the instance:

   .. code-block:: bash

      aws --profile="${AWS_PROFILE}" \
		   ec2 describe-instances --instance-ids "${INSTANCE_ID}"

   The output in JSON format, and should contain the following when the
   instance is ready:

   .. code-block:: text

      "State": {
        "Code": 16,
        "Name": "running"
      }

   Once runnuing, either the `PublicDnsName` or `PublicIPAddress` mentioned in
   same output can be used to connect to the instance via `ssh` using an
   ssh provided by a WormBase :term:`AWS` administrator.

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

   1. Extract all .ace files from the ACeDB database for the current release.
   2. Compress all .ace files
   3. Convert .ace files to EDN logs
   4. Sort all EDN logs by timestamp
   5. Create the Datomic database
   6. Import the EDN logs into the Datomic database
   7. Run a QA report on the database

      .. note:: Once this step has completed, the user is prompted to
         	confirm the next step, or abort.

   8. Transfer the Datomic database to Amazon S3 storage


.. _db-migration-step-3:

3. **Terminate the EC2 instance**

   .. code-block:: bash

      azanium --profile $USER admin stop-instance


Should all steps complete successfully, the migration process is now
complete.

If you stopped after :ref:`Step 2 <db-migration-step-2>` due to data
inconsistency, or an error occurred during any of the other steps,
please ensure to eventually run :ref:`Step 3 <db-migration-step-3>`.

Diagnostics
-----------
In the event of any errors, a `log file`_ should be written to the
:term:`S3` storage after each build step.
This log file should contain more information which may help developers fix the issue.


.. _`log file`: https://s3.amazonaws.com/wormbase/db-migration/azanium.log
