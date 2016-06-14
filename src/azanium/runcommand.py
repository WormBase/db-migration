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
@click.pass_context
def run(ctx):
    """Execute database migration on an ephemeral AWS EC2 instance.
    """
    ctx.obj = util.EC2InstanceCommandContext()


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
    logger.info('Dumped ACeDB files to {}', dump_dir)
    ctx = click.get_current_context()
    ctx.invoke(acedb_compress_dump, dump_dir)


@run.command()
@click.argument('dump_dir')
@util.pass_ec2_command_context
def acedb_compress_dump(context, dump_dir):
    gzip_cmd = ['find', dump_dir, '-type', 'f', '-name', '"*.ace"']
    gzip_cmd.extend([
        '|', 'xargs', '-n', '1', '-P', str(psutil.cpu_count()), 'gzip'
    ])
    util.local(gzip_cmd)
    logger.info('Compressed all .ace files in {}', dump_dir)


@run.command('init-datomic-db')
@click.argument('acedb_dump_dir')
@util.pass_ec2_command_context
def init_datomic_db(context, acedb_dump_dir):
    edn_logs_dir = context.path('edn_logs')
    datomic.configure_transactor(context, logger)
    logger.info('Creating datomic database')
    pseudoace.create_database(context, logger)
    pseudoace.acedb_dump_to_edn_logs(context,
                                     edn_logs_dir,
                                     acedb_dump_dir,
                                     logger)

@run.command()
@util.pass_ec2_command_context
def setup(context):
    util.local(['azanium', 'install'] + list(context.versions))
    acedb_dump_dir = context.path('acedb_dump')
    ctx = click.get_current_context()
    ctx.invoke(acedb_dump, dump_dir=acedb_dump_dir)
    ctx.invoke(init_datomic_db, acedb_dump_dir, java_cmd=context.java_cmd)


@run.command('sort-edn-logs')
@util.pass_ec2_command_context
def sort_edn_logs(context):
    pseudoace.sort_edn_logs(context, logger)


@run.command('qa-report')
@util.option('-b', '--build-data-path')
@util.pass_ec2_command_context
def qa_report(context, build_data_path):
    pseudoace.qa_report(context.java_cmd, logger)


@run.command('backup-database')
@util.pass_ec2_command_context
def backup_database(context):
    os.chdir(context.path('datomic_free'))
    datomic.backup_db(context.data_release_version, logger)
