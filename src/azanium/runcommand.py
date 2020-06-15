import collections
import datetime
import functools
import getpass
import gzip
import os
import psutil
import re
import shutil
import stat
import tarfile
import time
from functools import partial

import click

from . import artefact
from . import datomic
from . import log
from . import notifications
from . import pseudoace
from . import root_command
from . import util
from .install import installers

logger = log.get_logger(namespace=__name__)

LAST_STEP_OK_STATE_KEY = 'last-step-ok-idx'

@root_command.group()
@util.pass_command_context
def run(context):
    """Commands for executing the database migration."""


def acedb_id_catalog(
        meta,
        report_file_regexp='all_classes_report.{version}\.txt\.gz$'):
    """Installs the ACeDB id catalog use by QA report generation."""
    (host, path, version) = util.split_ftp_url(util.get_ftp_url())
    cwd = os.path.join(path, 'REPORTS')
    regexp = 'all_classes_report\.{}\.txt\.gz$'.format(version)
    downloaded = util.ftp_download(host,
                                   regexp,
                                   meta.download_dir,
                                   logger,
                                   initial_cwd=cwd)

    downloaded_path = downloaded[0]
    with gzip.open(downloaded_path) as gz_fp:
        filename = re.sub('^(?P<fn>.*)\.gz',
                          '\g<fn>',
                          os.path.basename(downloaded_path))
        out_path = os.path.join(meta.install_dir, filename)
        with open(out_path, 'wb') as fp:
            logger.info('Writing {}', fp.name)
            fp.write(gz_fp.read())
        return fp.name


@run.command('acedb-database', short_help='Downlaod the ACeDB database release.')
@util.option('--file-selector-regexp',
             default='.*\.tar\.gz$',
             help='File selection regexp')
@artefact.prepared
def acedb_database(context, afct, file_selector_regexp,
                   acedb_dir=None,
                   acedb_id_catalog_dir=None):
    """Fetches all data, then installs and configures the ACeDB database."""
    ctx = click.get_current_context()
    ftp_url = util.get_ftp_url()
    aidc_afct = artefact.prepare(context, acedb_id_catalog)
    ctx.invoke(acedb_id_catalog, aidc_afct, ftp_url)
    (host, path, version) = util.split_ftp_url(ftp_url)
    cwd = os.path.join(path, 'acedb')
    wspec_dir = os.path.join(afct.install_dir, 'wspec')
    ftp_get = functools.partial(util.ftp_download,
                                logger=logger,
                                initial_cwd=cwd)
    downloaded = ftp_get(host, file_selector_regexp, afct.download_dir)
    for path in downloaded:
        with tarfile.open(path) as tf:
            logger.info('Extracting {} to {}', path, afct.install_dir)
            tf.extractall(path=afct.install_dir)

    # Enable the Dump command (requires adding user to ACeDB pw file)
    passwd_path = os.path.join(wspec_dir, 'passwd.wrm')
    mode = 0o644
    logger.info('Changing permissions of {} to {}',
                passwd_path,
                stat.filemode(mode))
    os.chmod(passwd_path, mode)
    username = getpass .getuser()
    with open(passwd_path, 'a') as fp:
        logger.info('Adding {} to {}', username, passwd_path)
        fp.write(username + os.linesep)
    util.touch_dir(afct.install_dir)
    return afct.install_dir


@run.command('acedb-compress-dump',
             short_help='Compresses all ACeDB dump files.')
@click.argument('dump_dir')
@util.pass_command_context
def acedb_compress_dump(context, dump_dir):
    """gzip .ace files generated from an ACeDB dump (pseudoace compliance).
    """
    gzip_cmd = ['find', dump_dir, '-type', 'f', '-name', '"*.ace"']
    gzip_cmd.extend([
        '|',
        'xargs',
        '--no-run-if-empty',
        '-n', '1',
        '-P', str(psutil.cpu_count()),
        'gzip'
    ])
    util.local(gzip_cmd)
    logger.info('Compressed all .ace files in {}', dump_dir)


@run.command('acedb-dump', short_help='Dumps all ACeDB data to .ace files')
@util.option('-c',
             '--tace-dump-options',
             default='-s -T -C',
             help='tace "Dump" command options')
@click.argument('dump_dir')
@util.pass_command_context
def acedb_dump(context, dump_dir, tace_dump_options):
    """Dump the ACeDB database."""
    if os.path.isdir(dump_dir):
        return dump_dir
    db_directory = context.path('acedb_database')
    os.makedirs(dump_dir, exist_ok=True)
    dump_cmd = ' '.join(['Dump', tace_dump_options, dump_dir])
    logger.info('Dumping ACeDB files to {}', dump_dir)
    util.local('tace ' + db_directory, input=dump_cmd)
    return dump_dir


@run.command('create-database', short_help='Creates a Datomic database')
@click.argument('datomic_path')
@util.pass_command_context
def create_database(context, datomic_path):
    """Creates a Datomic datbase for importing EDN logs into."""
    datomic.configure_transactor(context, datomic_path)
    # Allow a small amount of time for the transactor to start
    time.sleep(2)
    pseudoace.create_database(context)
    return 'Created'


@run.command('acedb-dump-to-edn-logs',
             short_help='Converts .ace files to EDN logs')
@util.pass_command_context
@click.argument('acedb_dump_dir')
@click.argument('edn_logs_dir')
def ace_to_edn(context, acedb_dump_dir, edn_logs_dir):
    """Converts ACeDB dump files (.ace) to EDN log files."""
    pseudoace.acedb_dump_to_edn_logs(context, acedb_dump_dir, edn_logs_dir)
    # restart the transactor to force jvm return memory to speed up later steps.
    # wrapped with retries due to circusctl bug.
    util.retries(3, lambda : util.local('python -m circus.circusctl --timeout=5 restart datomic-transactor',
                                   timeout=6))
    return edn_logs_dir


@run.command('sort-edn-logs', short_help='Sorts EDN logs')
@click.argument('edn_logs_dir')
@util.pass_command_context
def sort_edn_logs(context, edn_logs_dir):
    """Sort the EDN logs by timestamp in preparation for Datomic import."""
    pseudoace.sort_edn_logs(context, edn_logs_dir)


@run.command('qa-report')
@click.argument('acedb_id_catalog')
@util.pass_command_context
def qa_report(context, acedb_id_catalog):
    """Performs a qualiity assurance report on the Database against an
    ACedB "id catalog".

    """
    report_path = pseudoace.qa_report(context, acedb_id_catalog)
    ws_version = util.get_data_release_version()
    title = 'QA report for {version} available in <{path}>'
    title = title.format(version=ws_version, path=report_path)
    pretext = ('*Please check this looks correct '
               'before backing-up the datomic database*')
    attachment = notifications.Attachment(title, pretext=pretext)
    return attachment


@run.command('import-logs')
@click.argument('edn_logs_dir')
@util.pass_command_context
def import_logs(context, edn_logs_dir):
    """Imports EDN logs into a Datomic database ."""
    pseudoace.import_logs(context, edn_logs_dir)


@run.command('apply-patches')
@util.pass_command_context
def apply_patches(context):
    """Convert ACe patches to EDN and transact to the local datomic database."""
    pseudoace.apply_patches(context)


@run.command('backup-db',
             short_help='Backup the Datomic db.')
@util.pass_command_context
def backup_db(context, db_name_suffix=None):
    """Back up the Datomic database to the local disk."""
    os.chdir(context.path('datomic_free'))
    click.echo('Please check the QA report looks correct.')
    data_release_version = util.get_data_release_version()
    if db_name_suffix is not None:
        db_name = '{}-{}'.format(data_release_version, db_name_suffix)
    else:
        db_name = data_release_version
    date_stamp = datetime.date.today().isoformat()
    local_backup_path = os.path.join(context.path('datomic-db-backup'),
                                     date_stamp,
                                     db_name)
    arcname = '{}.tar.xz'.format(db_name)
    archive_path = os.path.join(os.path.dirname(local_backup_path),
                                arcname)
    if not os.path.isdir(local_backup_path):
        datomic.backup_db(context, local_backup_path, db_name)
    if not os.path.isfile(archive_path):
        logger.info('Creating archive {} for upload', archive_path)
        with tarfile.open(archive_path, mode='w:xz') as tf:
            tf.add(local_backup_path, arcname=arcname)
    return 'Datomic database compressed to {bp}.'.format(bp=archive_path)


@root_command.command(
    'clean-previous-state',
    short_help='Removes data from a previous migration run.')
@util.pass_command_context
def clean_previous_state(context):
    to_remove = set(installers.commands) | {
        'acedb_database',
        'acedb_id_catalog',
        'acedb-dump',
        'edn-logs',
        'homol-edn-logs',
        'datomic-db-backup'
    }
    force_rmdir = partial(shutil.rmtree, ignore_errors=True)
    for name in to_remove:
        logger.info('Removing directory: {}', name)
        force_rmdir(context.path(name))
    try:
        os.remove(os.path.expanduser('~/.db-migration.db'))
    except OSError as err:
        # file removed manually perhaps?
        pass

@root_command.command('homol-import',
                      short_help='Creates the homology database')
@click.argument('acedump_dir')
@click.argument('log_dir')
@util.pass_command_context
def homol_import(context, acedump_dir, log_dir):
    pseudoace.homol_import(context, acedump_dir, log_dir)

Step = collections.namedtuple('Step', ('description', 'func', 'kwargs'))

LOGS_DIR = 'edn-logs'

def _get_steps(context):
    datomic_path = context.path('datomic_free')
    dump_dir = context.path('acedb-dump')
    id_catalog_path = context.path('acedb_id_catalog')
    logs_dir = context.path(LOGS_DIR)
    acedb_dir = context.path('acedb_database')
    acedb_id_catalog_dir = context.path('acedb_id_catalog')
    steps = [
        Step('Fetch ACeDB data for release',
             acedb_database,
             dict(acedb_dir=acedb_dir,
                  acedb_id_catalog_dir=acedb_id_catalog_dir)),
        Step('Dumping all ACeDB files',
             acedb_dump,
             dict(dump_dir=dump_dir)),
        Step('Compresssing all ACeDB files',
             acedb_compress_dump,
             dict(dump_dir=dump_dir)),
        Step('Creating Datomic database',
             create_database,
             dict(datomic_path=datomic_path)),
        Step('Converting ACeDB files to EDN logs',
             ace_to_edn,
             dict(acedb_dump_dir=dump_dir, edn_logs_dir=logs_dir)),
        Step('Sorting EDN logs by timestamp',
             sort_edn_logs,
             dict(edn_logs_dir=logs_dir)),
        Step('Import EDN logs into Datomic database',
             import_logs,
             dict(edn_logs_dir=logs_dir)),
        Step('Apply ACe patches from the PATCHES directory on the FTP site.',
             apply_patches,
             {}),
        Step('Running QA report on Datomic database',
             qa_report,
             dict(acedb_id_catalog=id_catalog_path)),
        Step('Backup main migration database.',
             backup_db,
             {}),
        Step('Create the homology database.',
             homol_import,
             dict(acedump_dir=dump_dir, log_dir=logs_dir)),
        Step('Backup the homology database',
             backup_db,
             dict(db_name_suffix='homol'))]
    return steps


def available_reset_steps(context):
    steps = _get_steps(context)
    last_ok_step_n = context.app_state[LAST_STEP_OK_STATE_KEY]
    avail_steps = collections.OrderedDict()
    for (step_n, t) in enumerate(steps[:last_ok_step_n - 1], start=1):
        avail_steps[step_n] = t.description
    return avail_steps


@root_command.command('reset-to-step',
                      short_help='Reset the migration to a previous step')
@util.pass_command_context
def reset_to_step(context):
    error = lambda msg: util.echo_error('ERROR: {}'.format(msg), notify=False)
    last_ok_step_n = context.app_state.get(LAST_STEP_OK_STATE_KEY)
    if not last_ok_step_n:
        error('Migration has not been run, cannot reset to any state.')
        click.get_current_context().exit(1)
    click.echo('Reset to previous migration step')
    click.echo(
        'The last step that completed successfully was: {}'.format(last_ok_step_n),
        nl=False)
    click.echo(color='green')
    click.echo()
    click.echo("""\
    WARNING!:

    It's responsibility to remove any state/files that have been created since
    the step you want to revert to.
    """, color='red')
    out_lines = []
    available_steps = available_reset_steps(context)
    for (step_n, step_desc) in available_steps.items():
        out_lines.append('Step {num}: {desc}'.format(num=step_n, desc=step_desc))
    separator = '-' * max(map(len, out_lines))
    click.echo(separator)
    for out_line in out_lines:
        click.echo(out_line)
    click.echo(separator)
    step_n_req = click.prompt('Reset to step',
                              default=abs(last_ok_step_n - 1),
                              type=int,
                              show_default=True)
    step_n_req -= 1
    if step_n_req < last_ok_step_n:
        if click.confirm('Reset step to {}?'.format(step_n_req), abort=True):
            context.app_state[LAST_STEP_OK_STATE_KEY] = step_n_req
    elif step_n_req > last_ok_step_n:
        error('Refusing to set migration step to a future step')
    step_n = context.app_state[LAST_STEP_OK_STATE_KEY]
    click.echo('Migration step is now set to {}'.format(step_n + 1))

def process_steps(context, steps):
    headline_fmt = 'Migrating ACeDB {release} to Datomic, *Step {step}*'
    release = util.get_data_release_version()
    ctx = click.get_current_context()
    step_idx = int(context.app_state.get(LAST_STEP_OK_STATE_KEY, '0'))
    step_n = step_idx + 1
    for (step_n, step) in enumerate(steps[step_idx:], start=step_n):
        step_command = partial(ctx.invoke, step.func, **step.kwargs)
        headline = headline_fmt.format(release=release, step=step_n)
        with logger:
            notifications.around(step_command,
                                 headline,
                                 step.description)
            # if a step (above) fails, an exception will be thrown (uncaught),
            # such that exception is propergated (i.e will be visible verbatim in slack)
            # only write the "last step ok" to disk when successful.
            context.app_state[LAST_STEP_OK_STATE_KEY] = step_n
    notifications.notify('{} migration'.format(release),
                         notifications.Attachment(title='*all done!*'),
                         icon_emoji=':fireworks:')

@root_command.command('migrate',
                      short_help='Run all db-migration steps.')
@util.pass_command_context
def migrate(context):
    """Steps:
        1. Dump ACeDB files (.ace files)

        2. Compress ACedB files using gzip

        3. Create Datomic Database

        4. Convert .ace files to EDN logs

        5. Sort EDN log files by timestamp

        6. Import EDN logs into Datomic database

        7. Apply any ACe patches from the PATCHES directory on the FTP site.

        8. Run QA Report on Datomic DB

        9. Backup Datomic database locally.

       10. Create homology database.

       11. Backup homology database.

    """
    steps = _get_steps(context)
    process_steps(context, steps)
