========
Releases
========
This package uses `zest.releaser`_ to automate the release process.
This automatically updates the `changelog.rst`, `setup.py` files
and handles tagging with `git` and pushing releases to github.

Having checked out the master *master* branch, and merged the
*develop* branch in:

#. Ensure the necessary dependencies and versions (particularly `pseudoace`),
   have been updated in the `src/azanium/cloud-config/versions.ini` file.

#. Edit the change-log to say what's been changed.
   Leave the header as:

   .. code-block:: text

      <version-number> (un-released)
      ------------------------------
      - <Your changelog entry here>

#. From the root of the project, run:


   .. code-block:: bash

      make release

   Accept the default on most questions, unless you are sure
   that's not what you want.

   (*Typically, it's safe to accept the default for all questions*)

db-migration deployment
-----------------------

After creating a new release, deploy the new version
on the wb-db-migration EC2 instance.

.. code-block:: bash

   # SSH into the `wb-db-migration` EC2 instance (as `ec2-user`)

   #Switch to datomic_build user (prevent permission problems)
   sudo -u datomic_build -i

   #Check the currently installed azanium version
   pip3 freeze | grep azanium

   #Install the latest azanium version (replace RELEASE_TAG)
   pip3 install --user "https://github.com/WormBase/db-migration/releases/download/${RELEASE_TAG}/azanium-${RELEASE_TAG}-py3-none-any.whl"

   #Check the new azanium version installed correctly
   pip3 freeze | grep azanium
   
   azanium --help


.. _`zest.releaser`: https://zestreleaser.readthedocs.io/en/latest
