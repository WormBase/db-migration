import os
import psutil

import click

from . import datomic
from . import log
from . import pseudoace
from . import util


logger = log.get_logger(__name__, verbose=True)


@click.group()
@util.log_level_option()
@click.pass_ec2_command_context
def run(ctx, log_level, java_cmd):
    log.setup_logging(log_level=log_level)
    ctx.obj = util.CommandContext()


@run.command()
@util.option('-c',
             '--tace-dump-options',
             default='-s -T -C',
             help='tace "Dump" command options')
@click.argument('dump_dir')
@util.pass_ec2_command_context
def acedb_dump(context, dump_dir, tace_dump_options):
    db_directory = context.path('acedb_database')
    os.makedirs(dump_dir, exist_ok=True)
    dump_cmd = ' '.join(['Dump', tace_dump_options, dump_dir])
    logger.info('Dumping ACeDB files to {}', dump_dir)
    util.local('tace ' + db_directory, input=dump_cmd)
    gzip_cmd = ['find', dump_cmd, '-type', 'f', '-name', '"*.ace"']
    gzip_cmd.extend([
        '|', 'xargs', '-n', '1', '-P', str(psutil.cpu_count()), 'gzip'
    ])
    util.local(gzip_cmd)
    logger.info('Dumped ACeDB files to {}', dump_dir)


@run.command('init-datomic-db')
@click.argument('acedb_dump_dir')
@util.pass_ec2_command_context
def init_datomic_db(context, acedb_dump_dir):
    edn_logs_dir = context.path('edn_logs')
    uri = context.datomic_url
    datomic.configure_transactor(context, logger)
    pseudoace.prepare_target_db(context.java_cmd,
                                uri,
                                edn_logs_dir,
                                acedb_dump_dir,
                                logger)


@run.command()
@util.pass_ec2_command_context
def setup(context):
    util.local(['wb-db-install'] + list(context.versions))
    acedb_dump_dir = context.path('acedb_dump')
    ctx = click.get_current_context()
    ctx.invoke(acedb_dump,
               dump_dir=acedb_dump_dir,
               db_directory=context.path('acedb_database'))
    ctx.invoke(init_datomic_db, acedb_dump_dir, java_cmd=context.java_cmd)


@run.command('sort-edn-logs')
@util.pass_ec2_command_context
def sort_edn_logs(context):
    pseudoace.sort_edn_logs(context, logger)


@run.command('qa-report')
@util.option('-b', '--build-data-path')
@util.pass_ec2_command_context
def qa_report(context, build_data_path):
    pseudoace.qa_report(context.java_cmd,
                        context.data_release_version,
                        build_data_path,
                        logger)


@run.command('backup-database')
@util.pass_ec2_command_context
def backup_database(context):
    os.chdir(context.path('datomic_free'))
    datomic.backup_db(context.data_release_version, logger)


cli = run()
