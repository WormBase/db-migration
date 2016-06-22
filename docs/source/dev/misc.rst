=================================================
Design decisions and other miscellaneous factoids
=================================================

UserData limitations
====================
Cannot transfer this package to the instance using UserData,
since with AWS UserData there's a hard limit of 16384 bytes.
Hence cloud-config is used just to specify the base O/S packages, and
perform initial security updates on the base (Amazon) AMI.  The
required software is later scp'd onto the machine using an ssh
transport.
