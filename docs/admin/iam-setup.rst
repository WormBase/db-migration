=============
AWS IAM setup
=============
The following instructions assume a fresh-setup of the database
migration, with no pre-existing groups, users, roles or policies
defined.

.. note::
   It's also assumed you have ``awscli`` python package installed

.. note:: The WormBase AWS account number and
          thus all custom ARNs have been elided within all examples.

Design
======
We attempt to follow best-practice in regard to security, thus;
the scheme for creating the requisite resources for database migration
involves a user `assuming a role_` rather then they, or their group
having the permission to perform all the required operations directly.

The rationale is that users do not typically require the full set of
permissions required to perform the build; thus it is best that they
are granted the ability to perform these operations only when needed.

:term:`IAM` setup tool
======================
For convenience, the `wormbase-db-migration` package provides a
:term:`CLI` for performing the *minimal* :term:`IAM` configuration
necessary for a migration to be performed.

.. code-block:: bash

   # Obtain a copy of the tarfile for code and run:
   pip3 install --user wormbase-db-migration.tar.gz
   wb-db-migrate setup_iam


Initial configuration
=====================
The remainder of the documentation here will assume the following alias.

The username referred to as ``${AWS_ADMIN_USERNAME}`` should have the
assigned the ``IAMFullAccess`` policy.

.. code-block:: bash

   alias iam="aws iam --profile=${AWS_ADMIN_USERNAME}"

Create the user group
=====================
Create a group for a `db-migration` user and attach the
``IAMReadOnlyAccess`` policy.

This should be the only policy attached to this group.

.. code-block:: bash

   GROUP_NAME="db-migration-users"
   iam create-group --group-name="${GROUP_NAME}"
   iam attach-group-policy \
		--group-name="${GROUP_NAME}" \
		--policy_arn="arn:aws:iam::aws:policy/IAMReadOnlyAccess"


Create the role to be assumed
=============================
Create the role that will be assume by `db-migration` users to
perform the migration steps.

Role policies
-------------
The following set of policies are currently required, and must be attached
to the role to be assumed:

`DecodeAuthorizationMessages`
  Allow decoding of error messages.

`IAMReadOnlyAccess`
  Allow listing of groups, users, roles and policies.

`ec2-manage-instances`
  Allow manipulation of EC2 instance profiles.

`ec2-manage-keypairs-and-security-groups`
  Allow the creation and deletion of key-pairs.

`ec2-manage-volumes`
  Allow the creation and deletion of instance volumes.

`ec2-run-db-migration-instances`
  Allow describing, starting,stopping and termination of instances.

`ec2-tagging`
  Allow assignment of tags to instances

`s3-datomic-backups-full-access`
  Allow backup of datomic database to a pre-designated :term:`S3` bucket.


.. note::

   The `ec2-run-db-migration-instances` policy is a copy of the
   custom WormBase policy `ec2-run-instances`;
   the difference between this policy and the original is that the
   value in the conditions that prevent users from touching others'
   resources uses `aws:user_id` as opposed to `aws:username`, since
   the later is not available when using the ``AssumeRole`` API.


Configure the Role's trust relationships
----------------------------------------
The role must be updated to specify the :term:`ARN` for each user who
will be granted permission to assume it.

The following is in example of the trust relationship document that needs to be
assigned to the role:

.. code-block:: json

   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Principal": {
         "AWS": [
	   "arn:aws:iam::...:user/username1",
	   "arn:aws:iam::...:user/username2",
	   "arn:aws:iam::...:user/username3"
         ]
       },
       "Action": "sts:AssumeRole"
     }]
   }

Adding or updating this trust relationship can be done via the AWS web console,
or via the CLI. When doing so via the CLI, the ARN for each policy must be used,
so this is not shown here.


.. code-block:: bash

   iam attach-role-policy --policy

In addition, each :term:`IAM` `user` must have a policy attached which
allows them to assume this role.

This policy allows states that the role is allowed to be assumed.

.. code-block:: json

    {
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
          "Action": "sts:AssumeRole",
          "Resource": "arn:aws:iam::...:role/wb-db-migrator"
      }]
    }



.. _`assuming a role`: http://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-console.html
