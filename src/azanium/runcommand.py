import os
import psutil
import tempfile

import click

from . import awscloudops
from . import root_command
from . import datomic
from . import install
from . import log
from . import notifications
from . import pseudoace
from . import util


logger = log.get_logger(namespace=__name__)


@root_command.group()
@util.pass_command_context
def run(context):
    """Commands for executing db migration on an ephemeral AWS EC2 instance.
    """


@run.command('acedb-compress-dump',
             short_help='Compresses all ACeDB dump files.')
@click.argument('dump_dir')
@util.pass_command_context
def acedb_compress_dump(context, dump_dir):
    """gzip .ace files generated from an ACeDB dump (pseudoace compliance).
    """
    gzip_cmd = ['find', dump_dir, '-type', 'f', '-name', '"*.ace"']
    gzip_cmd.extend([
        '|', 'xargs', '-n', '1', '-P', str(psutil.cpu_count()), 'gzip'
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
def acedb_dump(context, tace_dump_options, dump_dir):
    """Dump the ACeDB database."""
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
    return 'Created'


@run.command('acedb-dump-to-edn-logs',
             short_help='Converts .ace files to EDN logs')
@click.argument('acedb_dump_dir')
@click.argument('edn_logs_dir')
def ace_to_edn(context, acedb_dump_dir, edn_logs_dir):
    """Converts ACeDB dump files (.ace) to EDN log files."""
    pseudoace.acedb_dump_to_edn_logs(context, edn_logs_dir, acedb_dump_dir)
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
    key_template = 'db-migration/{}-report.html'
    bucket_path = key_template.format(context.versions['acedb_database'])
    with tempfile.NamedTemporaryFile(suffix='WS252-report.html') as fp:
        html_title = 'QA Report for {versions[acedb_database]}'
        html_title = html_title.format(versions=context.versions)
        html_report = pseudoace.qa_report_to_html(report_path, html_title)
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


@run.command('backup-db-to-s3',
             short_help='Transfers the Datomic db backup to S3')
@util.pass_command_context
def backup_db_to_s3(context):
    """Back up the Datomic database to Amazon S3 storage."""
    os.chdir(context.path('datomic_free'))
    datomic.backup_db(context.data_release_version)


@run.command('all-migration-steps', short_help='Runs all db migration steps')
@util.pass_command_context
def all_migration_steps(context):
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
    call = click.get_current_context().invoke
    logger.info('Step 0: Installing all required software')
    logs_dir = context.path('edn-logs')
    dump_dir = context.path('acedb-dump')

    installed = context.install_all_artefacts(install, call)
    datomic_path = installed['datomic_free']
    id_catalog_path = installed['acedb_id_catalog']

    steps = (
        ('Dumping all ACeDB files', acedb_dump, dump_dir),
        ('Compresssing all ACeDB files', acedb_compress_dump, dump_dir),
        ('Creating Datomic database', create_database, datomic_path),
        ('Converting ACeDB files to EDN logs', ace_to_edn, dump_dir, logs_dir),
        ('Sorting EDN logs by timestamp', sort_edn_logs, logs_dir),
        ('Import EDN logs into Datomic database', import_logs, logs_dir),
        ('Running QA report on Datomic database', qa_report, id_catalog_path),
    )
    for (step_n, step) in enumerate(steps, start=1):
        (message, step_command, *step_args) = step
        context.exec_step(step_n, message, step_command, *step_args)

    # Final step
    if input('Backup database to S3? [y/N]:').lower().startswith('y'):
        context.exec_step(step_n + 1,
                          backup_db_to_s3,
                          icon_emoji=':fireworks:')
