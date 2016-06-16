import os
import psutil

import click

from . import root_command
from . import datomic
from . import log
from . import pseudoace
from . import util


logger = log.get_logger(__name__, verbose=True)


@root_command.group()
@util.pass_command_context
def run(ctx):
    """Execute database migration on an ephemeral AWS EC2 instance.
    """


@run.command()
@click.argument('dump_dir')
@util.pass_command_context
def acedb_compress_dump(context, dump_dir):
    gzip_cmd = ['find', dump_dir, '-type', 'f', '-name', '"*.ace"']
    gzip_cmd.extend([
        '|', 'xargs', '-n', '1', '-P', str(psutil.cpu_count()), 'gzip'
    ])
    util.local(gzip_cmd)
    logger.info('Compressed all .ace files in {}', dump_dir)


@run.command()
@util.option('-c',
             '--tace-dump-options',
             default='-s -T -C',
             help='tace "Dump" command options')
@util.pass_command_context
def acedb_dump(context, tace_dump_options):
    db_directory = context.path('acedb_database')
    dump_dir = context.path('acedb_dump')
    os.makedirs(dump_dir, exist_ok=True)
    dump_cmd = ' '.join(['Dump', tace_dump_options, dump_dir])
    logger.info('Dumping ACeDB files to {}', dump_dir)
    util.local('tace ' + db_directory, input=dump_cmd)
    logger.info('Dumped ACeDB files to {}', dump_dir)
    click.get_current_context().invoke(acedb_compress_dump, dump_dir)
    return dump_dir


@run.command('prepare-import')
@click.argument('acedb_dump_dir')
@util.pass_command_context
def prepare_import(context, acedb_dump_dir):
    edn_logs_dir = context.path('edn-logs')
    datomic.configure_transactor(context, logger)
    pseudoace.create_database(context, logger)
    pseudoace.acedb_dump_to_edn_logs(context,
                                     edn_logs_dir,
                                     acedb_dump_dir,
                                     logger)
    return edn_logs_dir


@run.command()
@util.pass_command_context
def setup(context):
    util.local(['azanium', 'install'] + list(context.versions))
    acedb_dump_dir = context.path('acedb_dump')
    ctx = click.get_current_context()
    ctx.invoke(acedb_dump, dump_dir=acedb_dump_dir)
    ctx.invoke(prepare_import, acedb_dump_dir)
    return acedb_dump_dir


@run.command('sort-edn-logs')
@click.argument('edn_logs_dir')
@util.pass_command_context
def sort_edn_logs(context, edn_logs_dir):
    pseudoace.sort_edn_logs(context, logger, edn_logs_dir)


@run.command('qa-report')
@util.pass_command_context
def qa_report(context):
    pseudoace.qa_report(context, logger)


@run.command('import-logs')
@util.pass_command_context
def import_logs(context, edn_logs_dir):
    pseudoace.import_logs(context, edn_logs_dir, logger)


@run.command('backup-database')
@util.pass_command_context
def backup_database(context):
    os.chdir(context.path('datomic_free'))
    datomic.backup_db(context.data_release_version, logger)


@run.command('all')
def all_steps(context):
    ctx = click.get_current_context()
    steps = (
        acedb_dump,
        prepare_import,
        import_logs,
        qa_report,
        backup_database
    )
    logger.info('Step 0: Installing all required software')
    util.local(['azanium', 'install'] + list(context.versions))

    # Step 1: Dump and compress ACeDB files
    acedb_dump_dir = ctx.invoke(acedb_dump)

    # Step 2: Prepare import
    edn_logs_dir = ctx.invoke(prepare_import, acedb_dump_dir)

    # Step 3: Sort EDN logs
    ctx.invoke(sort_edn_logs, edn_logs_dir)

    # Step 4: Import Logs
    ctx.invoke(import_logs, edn_logs_dir)
    ctx.invoke(qa_report)
    ctx.invoke(backup_database)
