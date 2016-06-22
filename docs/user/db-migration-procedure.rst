
.. _db-migration-steps:

============================
Database Migration Procedure
============================
The following steps should be executed in order.

.. note:: You must have ``ssh-agent`` running in your shell session.

.. _db-migration-step-1:

1. Provision and bootstrap an EC2 instance

   The following :term:`azanium` sub-command below, when run, will
   print out the ssh commands needed for the next step.

   .. code-block:: bash

      AWS_PROFILE="${USER}"
      WB_DATA_RELEASE="WS254"
      azanium --profile "${USER}" cloud init "${WB_DATA_RELEASE}"

.. _db-migration-step-2:

2. Connect to the EC2 instance using ssh, run db-migration commands

   .. note::
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

.. _db-migration-step-3:

3. Terminate the EC2 instance

   .. warning::
      The following command will shut down the instance and destroy
      all data.

   .. code-block:: bash

      azanium cloud --profile $USER terminate


Should all steps complete successfully, the migration process is now
complete.

If you stopped after :ref:`Step 4 <db-migration-step-4>` due to data
inconsistency, or an error occurred during any of the other steps,
please ensure to eventually run :ref:`Step 5 <db-migration-step-5>`.
