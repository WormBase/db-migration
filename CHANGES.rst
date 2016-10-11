===========
 Changelog
===========

0.19 (2016-10-11)
=================

- Fixed issue in cleaning up previous migration.
- Allow Datomic URI to be overridden via environment variable.
- Minor fixes to docs.
- Bump data release version to WS256.
- Use the AWS_DEFAULT_PROFILE environment variable rather requiring user to
  specify with `--profile`.

0.18 (2016-08-10)
=================
- Cleanup data from any previous migration before starting a new one.
- Keep datomic backup directory on disk after S3 upload of tarfile to
  enable DDB restore.
- Reflect change in pseudoace 0.4.10 (Location of annotated ACeDB models file)
- Fixed issue with wrong path to QA id catalog input path.
- Fixed bucket S3 path for Datomic db backup.
- datomic-free does not support direct `s3` upload -
  work around that with local back and upload via AWS APIs.
- Updates to reflect switch to non-ephemeral instance.
- Bump data version to WS255.


0.17 (2016-06-27)
=================

- Minor updates to docs.


0.16 (2016-06-27)
=================

- Update install instructions in docs.


0.15 (2016-06-27)
=================

- Tweaks to documentation.


0.14 (2016-06-24)
=================

- Store application logfile in S3 at the end of each build step.
- Improved docs.

0.13 (2016-06-23)
=================

- Updated documentation to match release procedure changes.


0.12 (2016-06-23)
=================

- Fix name of entry point `zest.releaser` uses.


0.11 (2016-06-23)
=================
- Fix bug with release hook.


0.10 (2016-06-23)
=================

- Fix dependencies.
- Added `zest.releaser` hook to deploy code/docs to github/github-pages.
- Made the `migrate` command re-entrant.


0.9 (2016-06-23)
================

- Make this changelog show up in the docs.


0.8 (2016-06-23)
================

- Re-worked documentation to use `ghp-import` instead of travis-sphinx.
- Add post-release hook to deploy documentation via make-file.


0.7 (2016-06-22)
================

- Pass correct flags to `travis-sphinx` to get HTML docs built and deployed.


0.6 (2016-06-22)
================

- Fix typo in Sphinx configuration.

0.5 (2016-06-22)
================

- Use Sphinx's builtin githubpages extension.

0.4 (2016-06-22)
================

- Fixed issue with sphinx build (missing `docs/_static`)

0.3 (2016-06-22)
================

- Fix docs-build on travis.

0.2 (2016-06-22)
================

- Unified documentation.
- Unified all build steps into a single command `azanium migrate`.
- Add slack notifications for build progress.
- Prepare automation of documentation build to github pages.

0.1 (2016-06-22)
================

- Initial version.
