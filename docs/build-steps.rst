
.. _build-steps:

Build Steps
===========


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
      The ssh command(s) required to connect should have been printed
      by the command in step 2 above.

   Use the `ssh-add` and `ssh` commands printed from step 1, then issue
   the following commands in either `screen` or `tmux`.

   .. code-block:: bash

      # Create a new tmux session for performing the build.
      tmux new-session -s wb-db-build

   Install all required software and data (ACeDB, datomic, pseudoace),
   Dump `.ace` files from the current `ACeDB` data release, create a
   new Datomic database and converts all .ace files into EDN format:

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
   Should everything look OK, make a backup of the newly created
   database to Amazon S3, for use by the web team:

   .. code-block:: bash

      wb-db-run backup-db

.. _build-step-4:

4. Backup the database to :term:`S3` for use by the web team.

   Exit the :term:`tmux` or :term:`screen` session used to perform
   :ref:`Step 2 <build-step-2>` and :ref:`Step 3 <build-step-3>`.


.. _build-step-5:

5. Terminate the EC2 instance

   .. warning::
      The following command will shut down the instance and destroy
      all data.

   .. code-block:: bash

      wb-db-build --profile $USER terminate


The build is now complete.
