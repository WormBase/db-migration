===================
 Adding a new user
===================

The `wbadduser` script:

 - Adds a new AWS IAM user
 - Configures user with the "STS" role that needed to be assumed to
   perform migration tasks
 - Grants user relevant AWS IAM policies
 - Adds the user to the `wb-db-migration-users` AWS IAM group
 - Creates a linux user on the `wb-db-migration` AWS EC2 host.

The following tasks must be completed in order to setup a new user, capable of performing the migration:

 * An AWS administrator must use the `ec2-user` account on the
   `wb-db-migration` :term:`EC2` isntance to create a new user:

    .. code-block:: bash

       # variables:
       #  - KEY: path to SSH key
       #         Associated with the EC2 migration instance
       #         The key can be obtain from the "KeyPairs" section of the EC2
       #  - EC2_INST_ADDR address of the EC2 instance.
       #  - USER  The user-name for the user.
       #          Ideally use the same user-name the AWS IAM user to avoid confusion.
       # - USER_SSH_PUB_KEY the contents of the public SSH key for the user.
       # Both the key pair and the instance address can be obtained from the EC2
       # service (either via web management console or the command line tool)

       # Run a command on the remote instance to create a new (linux) user.
       ssh -i $KEY ec2-user@${EC2_INST_ADDR} wb-add-new-user $USER $USER_SSH_PUB_KEY
		    
 * The user must then setup their environment as per the :ref:`user
   guide <aws-client-configuration>`.


 

