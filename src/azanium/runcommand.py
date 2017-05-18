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
    bucket_path = key_template.format(context.versions['acedb_database'])
    with tempfile.NamedTemporaryFile(suffix='WS252-report.csv') as fp:
        title = 'QA Report for {versions[acedb_database]}'
        title = title.format(versions=context.versions)
        html_report = pseudoace.qa_report_to_html(report_path, title)
        fp.write(html_report.encode('utf-8'))
        invoke = click.get_current_context().invoke
        report_url = invoke(awscloudops.upload_file,
                            path_to_upload=fp.name,
                            path_in_bucket=bucket_path)
    title = 'QA report for {versions[acedb_database]} available at <{loc}>'
    title = title.format(versions=context.versions, loc=report_url)
    pretext = ('*Please check this looks correct '
               'before backing the datomic database*')
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
    archive_path = os.path.join(os.path.dirname(local_backup_path),
                                '{}.tar.xz'.format(data_release_version))
    arcname = os.path.basename(local_backup_path)
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


@root_command.command(short_help='Runs all db migration steps')
@util.pass_command_context
def migrate(context):
    """Run all database migrations steps.

    Steps:

        1. Dump ACeDB files (.ace files)

        2. Compress ACedB files using gzip

        3. Create Datomic Database

        4. Convert .ace files to EDN logs

        5. Sort EDN log files by timestamp

        6. Import EDN logs into Datomic database

        7. Run QA Report on Datomic DB

        8. Backup Datomic database to Amazon S3 storage **

    ** Only performed if you confirm report output looks good (7).

    """
    logs_dir = context.path('edn-logs')
    dump_dir = context.path('acedb-dump')
    datomic_path = context.path('datomic_free')
    id_catalog_path = context.path('acedb_id_catalog')
    headline_fmt = 'Migrating ACeDB {release} to Datomic, *Step {step}*'
    release = context.versions['acedb_database']
    conf = config.parse(section=notifications.__name__)
    ctx = click.get_current_context()
    step_idx = int(context.db_mig_state.get(LAST_STEP_OK_STATE_KEY, '0'))
    steps = []
    if not os.path.exists(context.path('acedb_database')):
        steps = [('Installing all software and ACeDB',
                  partial(install.all.invoke, ctx))]
    path_in_bucket = '/'.join(['db-migration',
                               os.path.basename(context.logfile_path)])
    upload_log_file = partial(ctx.invoke,
                              awscloudops.upload_file,
                              path_to_upload=context.logfile_path,
                              path_in_bucket=path_in_bucket)
    meta_steps = [
        ('Dumping all ACeDB files',
         acedb_dump,
         dict(dump_dir=dump_dir)),
        ('Compresssing all ACeDB files',
         acedb_compress_dump,
         dict(dump_dir=dump_dir)),
        ('Creating Datomic database',
         create_database,
         dict(datomic_path=datomic_path)),
        ('Converting ACeDB files to EDN logs',
         ace_to_edn,
         dict(acedb_dump_dir=dump_dir, edn_logs_dir=logs_dir)),
        ('Sorting EDN logs by timestamp',
         sort_edn_logs,
         dict(edn_logs_dir=logs_dir)),
        ('Import EDN logs into Datomic database',
         import_logs,
         dict(edn_logs_dir=logs_dir)),
        ('Running QA report on Datomic database',
         qa_report,
         dict(acedb_id_catalog=id_catalog_path)),
        ('Excising temporary data',
         excise_tmp_data,
         {}),
        (('@{user} - How does the report look?'
          'Please answer the question in ssh console session '
          'to backup the datomic database to S3, '
          'and complete the db migration '
          'process').format(user=context.user_profile),
         backup_db_to_s3,
         {})
    ]
    steps.extend(list((msg, partial(ctx.invoke, cmd, **kw))
                      for (msg, cmd, kw) in meta_steps))
    step_n = step_idx + 1
    for (step_n, step) in enumerate(steps[step_idx:], start=step_n):
        (message, step_command) = step
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
                                     message,
                                     post_kw=post_kw)
            finally:
                upload_log_file()
            context.db_mig_state[LAST_STEP_OK_STATE_KEY] = step_n - 1
