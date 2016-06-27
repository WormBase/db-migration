=================================
:term:`EC2` Instance requirements
=================================
The following tables describe the requisite properties of an EC2
instance the database migration procedure.

Instance details
================
IP and domain name addresses are not persisted beyond the life-time of
the instance.

+--------+----------+
|Username|ec2-user  |
+--------+----------+
|Type    |r3.4xlarge|
+--------+----------+
|Elastic |no        |
|IP      |          |
+--------+----------+
|region  |us-east-1 |
+--------+----------+


Storage
=======

+----------+-----------------+--------+-----+
|Device    |Moint-point      |Type    |Size |
+----------+-----------------+--------+-----+
|/dev/xvda1|/                |EBS     |60Gb |
|          |                 |        |SDD  |
+----------+-----------------+--------+-----+
|/dev/xvdb |/media/ephemeral9|Instance|30Gb |
|          |                 |Store   |SSD  |
+----------+-----------------+--------+-----+

Security properties
===================
The SSH key for accessing the instance is recycled automatically by the
`azanium init` command.

+--------+------------------------+
|Security|default                 |
|group   |                        |
+--------+------------------------+
|SSH Key |wb-db-migrate           |
|name    |                        |
+--------+------------------------+
|Local   |~/.ssh/wb-db-migrate.pem|
|SSH key |                        |
|path    |                        |
+--------+------------------------+
|Availble|22                      |
|ports   |                        |
+--------+------------------------+
