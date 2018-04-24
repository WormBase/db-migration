.. _db-migration-steps:

========
Commands
========
The following steps below will migrate the ACeDB database to Datomic.
Then end result will be a Datomic database stored on Amazon :term:`S3`,
which should be restored using the correct version of :term:`Datomic Pro`.

.. note:: You must have ``ssh-agent`` running in your shell session.

.. attention::

   Should the migration fail at any step, please ensure to eventually :ref:`stop <db-migration-stage-3>` the AWS instance.

.. _db-migration-step-1:

1. **Start the DB Migration EC2 instance**

   Having previously setup AWS Command Line Interface, using
   the `db migration ec2 instance id` provided by a WormBase AWS
   Administrator, enter the following :term:`aws cli` command to start
   the migration instance:

   .. code-block:: bash

      export AWS_PROFILE="${USER}" # WormBase AWS account username
      export INSTANCE_ID="${INSTANCE_ID_PROVIDED_BY_WORMBASE_AWS_ADMIN}"
      aws ec2 start-instances --instance-ids "${INSTANCE_ID}"

.. _db-migration-step-2:

2. **Connect to the EC2 instance using ssh - run the migrate command**

   Use the following command check the status of the instance:

   .. code-block:: bash

      aws ec2 describe-instances --instance-ids "${INSTANCE_ID}"

   The output in JSON format, and should contain the following when the
   instance is ready:

   .. code-block:: text

      "State": {
        "Code": 16,
        "Name": "running"
      }

   Once running, either the `PublicDnsName` or `PublicIPAddress`
   mentioned in same output can be used to connect to the instance via
   `ssh` using an ssh provided by a WormBase :term:`AWS`
   administrator.

   The commands below will emit their current progress to the console,
   and will also print out the location of a log file for more detailed
   output.

   Use the `ssh` command printed from step 1 to connect to the EC2 instance.

   .. note:: You may need to add the identity to ``ssh-agent`` first.

      .. code-block:: bash

   	ssh-add ~/.ssh/wb-db-migrate.pem

   Once connected to the EC2 instance via ssh, use either `screen` or
   `tmux` session, e.g:

   .. code-block:: bash

      tmux new-session -s azanium-commands


   Clean up after any previous migration:

   .. code-block:: bash

      azanium clean-previous-state

   Install the required software and data:

   .. code-block:: bash

      azanium install all

   Perform the migration:

   If any patches need to be loaded, then:

   azanium run acedb-dump

   .. code-block:: bash

      azanium migrate-stage-1

   This command will execute steps for stage 1 of the migration:

   1. Extract all .ace files from the ACeDB database for the current release.
   2. Compress all .ace files
   3. Convert .ace files to EDN logs
   4. Sort all EDN logs by timestamp


   .. attention::

      Now, from your *client* machine, restart the instance to free-up resources on the host (memory).

      .. code-block:: bash

   	aws ec2 restart-instances --instance-ids $INSTANCE_ID

   Run stage 2 of the migration:

   .. code-block:: bash

      azanium migrate-stage-2

   This command will execute steps for stage 2 of the migration:

   5. Create the Datomic database
   6. Import the EDN logs into the Datomic database
   7. Run a QA report on the database

      .. note:: Once this step has completed, the user will be prompted
	        in the tmux/screen shell session to confirm the next step, or abort.
	        This will also be posted to the slack channel for
	        tracking migration events.

   8. Transfer the Datomic database to Amazon S3 storage
   9. azanium backup-db
   10. Delete oldest WS database table in AWS DynamoDB and create the
       new one.

       .. code-block:: bash

	  aws dynamodb delete-table --table-name $OLDEST_WS_RELEASE
          aws dynamodb create-table --table-name $WS_RELEASE \
   	   --attribute-definitions AttributeName=id,AttributeType="S" \
           --key-schema KeyType="HASH",AttributeName="id"  \
           --provisioned-throughput ReadCapacityUnits=500,WriteCapacityUnits=500
   11. Transfer backed-up database to AWS S3

       .. code-block:: bash

	  FROM_URI="file:///wormbase/datomic-db-backups/$LATEST_DATE/$WS_RELEASE"
	  TO_URI="datomic:ddb://us-east-1/$WS_RELEASE/wormbase"

   11. With the corresponding version of datomic-pro installed in DATOMIC_HOME:
       .. code-block:: bash

	  cd $DATOMIC_PRO_HOME
          ./bin/datomic backup-db "$FROM_URI" "$TO_URI"

   12. Set the throughput values on the DynamoDB table for $WS_RELEASE
       to their lowest possible values.

   13. Write completion notification to the #db-migration-events
       wormbase-db-dev slack channel.


.. _db-migration-stage-3:

3. **Terminate the EC2 instance**

   .. code-block:: bash

      azanium admin stop-instance


Should all steps complete successfully, the migration process is now
complete.

Diagnostics
-----------
In the event of any errors, a `log file`_ should be written to the
:term:`S3` storage after each build step.
This log file should contain more information which may help developers fix the issue.


.. _`log file`: https://s3.amazonaws.com/wormbase/db-migration/azanium.log
