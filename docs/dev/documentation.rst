=============
Documentation
=============
As is common in most Python projects ;-

 * Markup is written and  in reStructuredText_ with Sphinx_
 * Output is generated using the Sphinx_ builder.

Generating
==========
For each target audience member (Admins, Developers and Users),
there is a separate set of documentation.

.. code-block:: bash

   make admin-docs dev-docs user-docs

The commands above will build the documentation in various formats
(Currently: HTML, man-page, text) in a corresponding sub-directory of
the current working directory.

Example 1 - View the generated text documentation for admins:

.. code-block:: bash

   less ./docs/admin/_build/text/index.txt

Example 2 - View then generated man page for developers:

   man -l ./docs/dev/_build/man/azanium.1

Example 3 - Vuew the generated HTML user documentation

   python -m webbrowser ./docs/user/_build/html/index.html


Distributing
============
TBD (github pages?)

.. _reStructuredText: http://www.sphinx-doc.org/en/stable/rest.html
.. _Sphinx: http://www.sphinx-doc.org/en/stable/
