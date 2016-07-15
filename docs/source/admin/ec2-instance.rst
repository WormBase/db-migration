=================================
:term:`EC2` Instance requirements
=================================
The following tables describe the requisite properties of an EC2
instance the database migration procedure.

Instance details
================
IP and domain name addresses are not persisted beyond the life-time of
the instance.

+-----------+----------+
|Username   |ec2-user  |
+-----------+----------+
|Type       |r3.4xlarge|
+-----------+----------+
|Elastic IP |no        |
+-----------+----------+
|region     |us-east-1 |
+-----------+----------+


Storage
=======
The follow properties represent the minimum storage requirements for
performing a database migration.

+----------+------------------+--------------------+----------+
|Device    |Mount-point       |Type                |Size      |
+----------+------------------+--------------------+----------+
|/dev/xvda1|/                 |EBS, SSD            |60Gb      |
+----------+------------------+--------------------+----------+
|/dev/xvdb |/wormbase         |Instance Store, SSD |320Gb     |
+----------+------------------+--------------------+----------+

Security properties
===================
The SSH key for accessing the instance is recycled automatically by the
`azanium init` command.

+------------------+--------------------------+
|Security group    |default                   |
+------------------+--------------------------+
|SSH Key name      |wb-db-migrate             |
+------------------+--------------------------+
|Local SSH key path|~/.ssh/wb-db-migrate.pem  |
+------------------+--------------------------+
|Available ports   | 22                       |
+------------------+--------------------------+
