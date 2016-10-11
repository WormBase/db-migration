=============
Documentation
=============
As is common in most Python projects ;-

 * Markup is written and  in reStructuredText_ with Sphinx_
 * Output is generated using the Sphinx_ builder.

Generating
==========

.. code-block:: bash

   make docs

The command above builds the documentation in various formats.
(Currently: *HTML*, *man-page* and *text*)

Example 1 - View the generated text documentation for admins:

.. code-block:: bash

   less ./docs/build/text/index.txt

Example 2 - View then generated man page for developers:

   man -l ./docs/build/man/azanium.1

Example 3 - Vuew the generated HTML user documentation

   python -m webbrowser ./docs/build/html/index.html

Distributing
============
This documentation is automatically deployed to github-pages when a
release is made (push and/or tag made on the `master` branch), via a
`zest.releaser entry-point`_.

.. _reStructuredText: http://www.sphinx-doc.org/en/stable/rest.html
.. _Sphinx: http://www.sphinx-doc.org/en/stable/
.. _`zest.releaser entry-point`: https://zestreleaser.readthedocs.io/en/latest/entrypoints.html
