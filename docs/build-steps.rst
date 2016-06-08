
.. _build-steps:

Build Steps
===========
The following steps should be executed in order.

.. _build-step-1:

1. Bootstrap an EC2 instance for performing the build

   The following `wb-db-build` command below, when run, will print out
   the ssh commands needed for the next step.

   .. code-block:: bash

      AWS_PROFILE="${USER}"
      WB_DATA_RELEASE="WS254"
      WB_DB_RELEASE_TAG="0.1"
      wb-db-build --profile $USER \
		   init \
   		   "dist/wormbase-db-build-${WB_DB_RELEASE}.tar.gz" \
		   "${WB_DATA_RELEASE}"


.. _build-step-2:

2. Connect to the EC2 instance using ssh, run build commands

   .. note::
	The commands below will emit their current progress to the console,
	and will also print out the location of a log file for more detailed
	output.


   Use the `ssh-add` and `ssh` commands printed from step 1, then issue
   the following commands in either `screen` or `tmux`.

   .. code-block:: bash

      # Create a new tmux session for watching logs, detach immediately
      tmux new-session -s wb-db-run-logs \; detach

      # Create a new tmux session for issuing commands
      tmux new-session -s wb-db-run \; detach


   Install all required software and data (:term:`ACeDB`,
   :term:`Datomic`, :term:`pseudoace`),
   Dump `.ace` files from the current :term:`ACeDB` data release, create a
   new :term:`Datomic` database and converts all .ace files into EDN format:

   .. code-block:: bash

      wb-db-run setup

   Sort the EDN log files by timestamp:

   .. ATTENTION:: The following command will take approximately 5-8 hours

   .. code-block:: bash

      wb-db-run sort-edn-logs

   Import the sorted EDN logs into datomic.

   .. ATTENTION:: The following command will take approximately 72 hours

   .. code-block:: bash

      wb-db-run import-logs


.. _build-step-3:

3. Run the QA report on the newly created database

   .. code-block:: bash

      wb-db-run qa-report

   Examine the report outputted by the previous command.
   Check the output of the report before continuing
   with :ref:`the next step <build-step-4>`.

.. _build-step-4:

4. Backup the database to :term:`S3` for use by the web team.

   Should you be content with the output of the QA
   report in :ref:`previous step <build-step-3>`, proceed to
   create a backup of the :term:`Datomic` database to :term:`S3`:

   .. code-block:: bash

      wb-db-run backup-db

   Exit the :term:`tmux` or :term:`screen` session and log off the EC2
   instance.

.. _build-step-5:

5. Terminate the EC2 instance

   .. warning::
      The following command will shut down the instance and destroy
      all data.

   .. code-block:: bash

      wb-db-build --profile $USER terminate


Should all steps complete successfully, the migration process is now
complete.

If you stopped after :ref:`Step 4 <build-step-4>` due to data
inconsistency, or an error occurred during any of the other steps,
please ensure to eventually run :ref:`Step 5 <build-step-5>`.
