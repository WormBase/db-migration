========
Releases
========
This package uses `zest.releaser`_ to automate the release process.
Automatically updates the `CHANGES.rst`, `setup.py` files and handles
tagging with `git` and pushing releases to github.

1. Make changes to the code and docs.
2. Edit the change-log to say what's been changed.
   Leave the header as:

   .. code-block:: text

	<version-number> (un-released)
	------------------------------
	- <Your changelog entry here>

3. From the root of the project, run:


   .. code-block:: bash

      make release

   Answer yes to most questions unless you are sure that's not what you want.

   (*Typically, it's safe to answer "Yes" to all questions*)


.. _`zest.releaser`: https://zestreleaser.readthedocs.io/en/latest
