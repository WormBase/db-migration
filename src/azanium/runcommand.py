import collections
import datetime
import os
import psutil
import shutil
import tarfile
import tempfile
import time
from functools import partial

from botocore.exceptions import ClientError
import click

from . import awscloudops
from . import config
from . import datomic
from . import install
from . import log
from . import notifications
from . import pseudoace
from . import root_command
from . import util


logger = log.get_logger(namespace=__name__)

LAST_STEP_OK_STATE_KEY = 'last-step-ok-idx'


@root_command.group()
@util.pass_command_context
def run(context):
    """Commands for executing db migration on an AWS EC2 instance."""


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
    key_template = 'db-migration/{}-report.csv'
    ws_version = context.versions['acedb_database']
    bucket_path = key_template.format(ws_version)
    title = 'QA Report for {}'
    title = title.format(ws_version)
    invoke = click.get_current_context().invoke
    report_url = invoke(awscloudops.upload_file,
                        path_to_upload=report_path,
                        path_in_bucket=bucket_path)
    title = 'QA report for {versions[acedb_database]} available at <{loc}>'
    title = title.format(versions=context.versions, loc=report_url)
    pretext = ('*Please check this looks correct '
               'before backing-up the datomic database*')
    attachment = notifications.Attachment(title, pretext=pretext)
    return attachment


@run.command('import-logs')
@util.pass_command_context
def import_logs(context, edn_logs_dir):
    """Imports EDN logs into a Datomic database ."""
    pseudoace.import_logs(context, edn_logs_dir)


@run.command('excise-tmp-data',
             short_help='Excise temporaty data')
@util.pass_command_context
def excise_tmp_data(context):
    """Excise temporary data from the migrated datomic database."""
    pseudoace.excise_tmp_data(context)


@run.command('backup-db-to-s3',
             short_help='Transfers the Datomic db backup to S3')
@util.pass_command_context
def backup_db_to_s3(context):
    """Back up the Datomic database to Amazon S3 storage."""
    os.chdir(context.path('datomic_free'))
    click.echo('Does the QA report looks correct?')
    prompt = 'Backup Datomic Database to S3? [y/N]:'
    if not input(prompt).lower().startswith('y'):
        click.get_current_context().abort()
    data_release_version = context.data_release_version
    date_stamp = datetime.date.today().isoformat()
    local_backup_path = context.path('datomic-db-backup')
    local_backup_path = os.path.join(local_backup_path,
                                     date_stamp,
                                     context.db_name)
    arcname = '{}.tar.xz'.format(data_release_version)
    archive_path = os.path.join(os.path.dirname(local_backup_path),
                                arcname)
    if not os.path.isdir(local_backup_path):
        datomic.backup_db(context, local_backup_path)
    if not os.path.isfile(archive_path):
        with tarfile.open(archive_path, mode='w:xz') as tf:
            tf.add(local_backup_path, arcname=arcname)
    ctx = click.get_current_context()
    try:
        s3_uri = ctx.invoke(awscloudops.upload_file,
                            path_to_upload=archive_path,
                            path_in_bucket='db-migration/' + arcname)
    except ClientError:
        logger.error('Failed to upload file to S3')
        logger.exception()
        raise
    else:
        logger.info('Removing local datomic db backup archive {}', archive_path)
        logger.info('Leaving datomic backup directory {} in place',
                    local_backup_path)
        os.remove(archive_path)
    return 'Datomic database transferred to {uri}.'.format(uri=s3_uri)


@root_command.command(
    'clean-previous-state',
    short_help='Removes data from a previous migration run.')
@util.pass_command_context
def clean_previous_state(context):
    to_remove = set(context.versions) | {
        'acedb-dump',
        'edn-logs',
        'datomic-db-backup'
    }
    force_rmdir = partial(shutil.rmtree, ignore_errors=True)
    for name in to_remove:
        force_rmdir(context.path(name))
    try:
        os.remove(os.path.expanduser('~/.db-migration.db'))
    except OSError as err:
        # file removed manually perhaps?
        print(err)

Step = collections.namedtuple('Step', ('description', 'func', 'kwargs'))

LOGS_DIR = 'edn-logs'

def _get_convert_steps(context):
    dump_dir = context.path('acedb-dump')
    logs_dir = context.path(LOGS_DIR)
    datomic_path = context.path('datomic_free')
    steps = [
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
             dict(edn_logs_dir=logs_dir))]
    return steps

def _get_import_steps(context):
    logs_dir = context.path(LOGS_DIR)
    id_catalog_path = context.path('acedb_id_catalog')
    steps = [
        Step('Import EDN logs into Datomic database',
             import_logs,
             dict(edn_logs_dir=logs_dir)),
        Step('Running QA report on Datomic database',
             qa_report,
             dict(acedb_id_catalog=id_catalog_path))]
    return steps


def available_reset_steps(context):
    steps = _get_convert_steps(context) + _get_import_steps(context)
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
    if step_n_req < last_ok_step_n:
        if click.confirm('Reset step to {}?'.format(step_n_req), abort=True):
            context.app_state[LAST_STEP_OK_STATE_KEY] = step_n_req
    elif step_n_req > last_ok_step_n:
        error('Refusing to set migration step to a future step')
    step_n = context.app_state[LAST_STEP_OK_STATE_KEY]
    click.echo('Migration step is now set to {}'.format(step_n))

def process_steps(context, steps):
    headline_fmt = 'Migrating ACeDB {release} to Datomic, *Step {step}*'
    release = context.versions['acedb_database']
    conf = config.parse(section=notifications.__name__)
    path_in_bucket = '/'.join(['db-migration',
                               os.path.basename(context.logfile_path)])
    ctx = click.get_current_context()
    upload_log_file = partial(ctx.invoke,
                              awscloudops.upload_file,
                              path_to_upload=context.logfile_path,
                              path_in_bucket=path_in_bucket)
    step_idx = int(context.app_state.get(LAST_STEP_OK_STATE_KEY, '0'))
    step_n = step_idx + 1
    for (step_n, step) in enumerate(steps[step_idx:], start=step_n):
        step_command = partial(ctx.invoke, step.func, **step.kwargs)
        headline = headline_fmt.format(release=release, step=step_n)
        with logger:
            if step_idx == len(steps):
                post_kw = dict(icon_emoji=':fireworks:')
            else:
                post_kw = {}
            try:
                notifications.around(step_command,
                                     conf,
                                     headline,
                                     step.description,
                                     post_kw=post_kw)
            finally:
                upload_log_file()
            context.app_state[LAST_STEP_OK_STATE_KEY] = step_n - 1

@root_command.command('migrate-stage-1',
                      short_help='Run initial db migration steps.')
@util.pass_command_context
def migrate_stage_1(context):
    """Steps:
        1. Dump ACeDB files (.ace files)

        2. Compress ACedB files using gzip

        3. Create Datomic Database

        4. Convert .ace files to EDN logs

        5. Sort EDN log files by timestamp
    """
    steps = []
    ctx = click.get_current_context()
    if os.path.exists(context.path('acedb_database')):
        steps = [('Installing all software and ACeDB',
                  partial(install.all.invoke, ctx))]
    steps.extend(_get_convert_steps(context))
    process_steps(context, steps)

@root_command.command('migrate-stage-2',
                      short_help='Completes db migration steps')
@util.pass_command_context
def migrate_stage_2(context):
    """Import the EDN files into datomic.

    Steps:

        6. Import EDN logs into Datomic database

        7. Run QA Report on Datomic DB

        8. Backup Datomic database to Amazon S3 storage **

    ** Only performed if you confirm report output looks good (7).

    """
    steps = _get_import_steps(context)
    steps.append(Step(('@{user} - How does the report look?'
                       'Please answer the question in ssh console session '
                       'to backup the datomic database to S3, '
                       'and complete the db migration '
                       'process').format(user=context.user_profile),
                      backup_db_to_s3,
                      {}))
    process_steps(context, steps)
