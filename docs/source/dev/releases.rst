========
Releases
========
This package uses `zest.releaser`_ to automate the release process.
Automatically updates the `CHANGES.rst`, `setup.py` files and handles
tagging with `git` and pushing releases to github.

TODO
   In the future, this will also build and upload the package
   using `python setup.py sdist` and place the bundle somewhere
   which can be downloaded by the automated AWS instance build.

Typically:

1. Make changes to the code
2. Edit the change-log to say what's been changed.
   Leave the header as:

   .. code-block:: text

	<version-number> (un-released)
	------------------------------
	- <Your changelog entry here>

3. From within a virtualenv with the package installed, run:

   ... code-block:: bash

   	fullrelease

   Answer yes to most questions unless you are sure that's not what you want.


.. _`zest.releaser`: https://zestreleaser.readthedocs.io/en/latest
