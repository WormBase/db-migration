===========
 Changelog
===========

0.7.14 (unreleased)
===================

- Nothing changed yet.


0.7.13 (2020-11-23)
===================

- Bumped pseudoace dependency version to bugfix migrate-homol DB naming (mismatch between pseudoace and azanium)
- Corrected ws_release_tag git tag availability check
- Changed WB release name parsing strategy, now tag-based rather than FTP-path based (WormBase/db-migration#41)
- Github authorization update (fix WormBase/db-migration#40)
- Fixed release creation vs tagging mismatch (fix WormBase/db-migration#42)


0.7.12 (2020-09-22)
===================

- Updated & completed docs
- Bugfixed migrate-homol DB name and DB backup file generation
- Minor logging and code improvements


0.7.11 (2020-07-16)
===================

- Updated pseudoace dependency version


0.7.10 (2020-07-09)
===================

- Cleanup downloaded artefacts in /tmp


0.7.9 (2020-07-08)
==================

- Specify release tag when configuring.
- Source annotated models from a configured github release tag.


0.7.8 (2020-06-23)
==================

- Fixed backup-db step for homology migration.


0.7.7 (2020-06-22)
==================

- Bump version of pseudoace.


0.7.6 (2020-06-19)
==================

- Increase transactor start wait time.


0.7.5 (2020-06-19)
==================

- Configure and start transactor before homol migration run.
- Fixed slack notify invocation at end of main migration.


0.7.4 (2020-06-16)
==================

- Fixed temp directory cleanup in installers.


0.7.3 (2020-06-16)
==================

- Bumped version of pseudoace to 0.7.3 (bring in CLI fix).


0.7.2 (2020-06-15)
==================

- Added separate top-level command for running homology migration.
- Bumped version of pseudoace to 0.7.2 to bring in fixes for homology command.

0.7.1 (2020-06-07)
==================

- Bring in pseudoace 0.7.1 for import-logs command line bug fix.

0.7.0 (2020-04-06)
==================

- Bumped version of pseduoace for CLI homology command fix.


0.60 (2020-03-19)
=================

- Bumped version of pseudoace to bring in bug-fix for homology pipeline.


0.59 (2020-03-13)
=================

- Fixed issue with datomic_free installer not being re-entrant.


0.58 (2020-03-13)
=================

- Ensured error messages are echoed to console during preliminary checks.


0.57 (2020-01-20)
=================

- Fixed recording/resetting of current step.
- Fixed click integration for homology import command.


0.56 (2020-01-09)
=================

- Fixed command to populate homology db.


0.55 (2020-01-06)
=================

- Provide default for `db_name` when invoking Context.datomic_url.


0.54 (2019-12-03)
=================

- Apply retry logic when restarting datomic transactor.
- Bumped version of pseudoace.
- Added two new steps to the migration process (produce homology database).


0.53 (2019-10-08)
=================

- Bumped version of pseudoace for bug fixes.


0.52 (2019-09-09)
=================

- Pull in new version of pseudoace for bugfix.


0.51 (2019-09-03)
=================

- Bumped version of pseudoace to pull in bugfix.

0.50 (2019-09-03)
=================

- Bumped version of pseudoace to pull in bugfix.


0.49 (2019-08-30)
=================

- Bumped version of pseudoace.


0.48 (2019-08-29)
=================
- Fixed locating of pseudoace release archive.


0.47 (2019-07-18)
=================
- Modify the way pseudoace is invoked via java jar file.
- Apply any patches from the PATCHES directory on the FTP site.


0.46 (2018-12-11)
=================
- Addressed github-reported security vulnerability in package dependencies.


0.45 (2018-12-11)
=================
- Bumped versions of datomic and pseudoace.


0.44 (2018-10-24)
=================
- Updated to latest version of pseudoace.
- Fixed typo (#35)
- Added missing requriement.

0.43 (2018-06-26)
=================
- Configuration of WormBase FTP URL an Slack URL done via configure command.
- Made slack configuration optional, persistent across migration runs.
- Downloading of ACeDB data moved from install step as the first migration step.
- Various bug fixes around the configuration command.
- Updated documentation to match changes to commands.

0.41 (2018-06-19)
=================
- Fixed bootstrapping issue.

0.40 (2018-06-19)
=================

- The FTP URL is now passed to the `azanium configure` command,
  rather than partially parameterised in install commmand(s).
- Fixed bugs with configuration code and logging.


0.39 (2018-06-18)
=================

- Removed all AWS specific code, documentation and configuration.


0.38 (2018-06-12)
=================

- Fixed dependency issue with `awscli`.
- Improved docs.

0.37 (2018-06-12)
=================

- Updated versions for the next migration run.


0.36 (2018-04-24)
=================

- Added admin script for adding new AWS IAM and EC2-host linux user.
- Updated documentation for multi-user migration.

0.35 (2018-04-19)
=================

- Use FTP staging area to obtain ACeDB release and class report.
- Improved docs.

0.34 (2018-04-19)
=================

- Bumped software versions.
- Updated notification docs.
- Fixed syntax errors.

0.33 (2018-03-06)
=================

- Split migration into two stages to speed up the process.
- Fix issue with upgrading package dependencies on install (docs)
- Updated documentation.


0.32 (2018-03-05)
=================
- Bumped versions for corresponding versions in pseudoace (WS264 + datomic).

0.31 (2017-12-18)
=================
- Release to fix release-script malfunction (!).

0.30 (2017-12-18)
=================
- Updated python requirements.

0.29.un-released (2017-12-18)
=============================
- Bump versions for next migration run.

0.28 (2017-10-30)
=================
- Addition of new command "reset-to-step".
- clean-previous-state command now removes app state file.
- Bump versions for next migration run.

0.27 (2017-09-11)
=================
- Source annotated models from release-tag in the
  `Wormbase/wormbase-pipeline` repository
- Fixed issue with notifications configuration where configuration
  could potentially be overridden.
- Bumped versions for next migration run.

0.26 (2017-07-07)
=================
- Bumped version of pseudoace.
- Bumped version of datomic-free.
- Bumped release version.
- Removed excise-tmp-data step.

0.25 (2017-05-19)
=================
- Bumped version of pseudoace.
- Allow migrate command to work with existing ACeDB database
  and corresponding pre-gzipped output.

0.24 (2017-04-27)
=================
- Bumped data release and pseudoace versions.

0.23 (2017-02-16)
=================
- Bumped data release version.

0.22 (2017-02-16)
=================
- Bumped versions.

0.21 (2016-11-19)
=================
- Bumped versions.

0.20 (2016-11-19)
=================
- Download the annotated models file separately (Fixes #8).
- Fix last step (backup and transfer to S3)

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
