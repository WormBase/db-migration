===============
Build procedure
===============

.. note::

   The following assumes you have used `$USER` as the name of the profile when
   configuring the AWS cli as above.

.. _build-step-1:

1. Configure an AWS account

   A WormBase AWS administrator should have previously supplied
   credentials that should be given as input to the following command:

   .. code-block:: bash

      aws configure --profile $USER

.. _build-step-2:

2. Provision and start an instance for doing the database-migration build

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

.. _build-step-3:

3. Run commands on the instance to perform the actual build-steps

   Use the `ssh-add` and `ssh` commands printed from step 1, then issue
   the following commands in either `screen` or `tmux`.

   .. code-block:: bash

      # Create a new tmux session for peforming the build.
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


.. _build-step-4:


4. Run the QA report on the newly created database and transfer database

   .. code-block:: bash

      wb-db-run qa-report

   Examine the report outputted by the previous command.
   Should everything look OK, make a backup of the newly created
   database to Amazon S3, for use by the web team:

   .. code-block:: bash

      wb-db-run backup-db

   Exit the `tmux` or `screen` session used to perform :ref:`Step 3
   <build-step-3>` and :ref:`Step 4 <build-step-4>`.
