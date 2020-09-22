=============
Documentation
=============
As is common in most Python projects:

 * Markup is written in reStructuredText_ (and Sphinx_)
 * Output is generated using the Sphinx_ builder.

Generating
==========

.. code-block:: bash

   make docs

The command above builds the documentation in HTML.
Multiple format-generations are supported: *html*, *man* (man-page) and *text*.

To generate docs in any format:

.. code-block:: bash

   make -C docs/ <format>

Viewing
=======

To view generated with the steps above
, use one of the examples below:

 * text documentation (for admins):

   .. code-block:: bash

      less ./docs/build/text/index.txt

 * man page (for developers):

   .. code-block:: bash

      man -l ./docs/build/man/azanium.1

 * HTML user documentation

   .. code-block:: bash

      python -m webbrowser ./docs/build/html/index.html

Distributing
============
This documentation is automatically deployed to github-pages when a
release is made (push and/or tag made on the `master` branch), via a
`zest.releaser entry-point`_.

.. _reStructuredText: http://www.sphinx-doc.org/en/stable/rest.html
.. _Sphinx: http://www.sphinx-doc.org/en/stable/
.. _`zest.releaser entry-point`: https://zestreleaser.readthedocs.io/en/latest/entrypoints.html
