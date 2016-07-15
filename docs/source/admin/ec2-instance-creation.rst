=========================
AWS EC2 Instance Creation
=========================
The instance to be used for the db migration should be created with
the following command:

.. code-block:: bash

   RELEASE="WS...."
   SUBNET_ID="subnet-xxxxx"
   azanium --profile="${AWS_CLI_ADMIN_ACCOUNT}" \
	 cloud init "${RELEASE}" "${subnet_id}"

In the above, `SUBNET_ID` should be the id of the subnet in the new
EC2-VPC named "wormbase".

The command above in effect,  wraps the typical `aws ec2 run-instances` command to install the `azanium` software on the instance, and pre-configure the instance with
`UserData`, as follows:

.. literalinclude:: ../../../src/azanium/cloud-config/AWS-cloud-config-UserData.template
