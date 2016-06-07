import glob
import multiprocessing
import os
import time

import click
from configobj import ConfigObj

from .logging import get_logger
from .logging import setup_logging
from .util import get_deploy_versions
from .util import install_path
from .util import local
from .util import log_level_option
from .util import option
from .util import pkgpath
from .util import sort_edn_log


logger = get_logger(__name__, verbose=True)


@click.group()
@log_level_option()
@click.pass_context
def run(ctx, log_level):
    setup_logging(log_level=log_level)


@run.command()
@option('-c',
        '--tace-dump-options',
        default='-s -T -C',
        help='tace "Dump" command options')
@option('-d',
        '--db-directory',
        help='The directory containing the ACeDB database files.')
@click.argument('dump_dir')
@click.pass_context
def acedb_dump(ctx, dump_dir, tace_dump_options, db_directory=None):
    if db_directory is None:
        db_directory = os.environ['ACEDB_DATABASE']
    os.makedirs(dump_dir, exist_ok=True)
    dump_cmd = ' '.join(['Dump', tace_dump_options, dump_dir])
    logger.info('Dumping ACeDB files to {}', dump_dir)
    local('tace ' + db_directory, input=dump_cmd)
    local('gzip {}/*.ace'.format(dump_dir))
    logger.info('Dumped ACeDB files to {}', dump_dir)


def configure_transactor(logger, conf_target_path, datomic_dist_dir):
    path = pkgpath(
        'cloud-config/circus-datomic-free-transactor.ini.template')
    transactor_properties_path = pkgpath(
        'cloud-config/datomic-free-transactor.ini')
    logger_config = pkgpath(
        'cloud-config/circus-logging-config.yaml')
    with open(path) as infile:
        conf = ConfigObj(infile=infile)
    transactor_cmd = ' '.join([
        '{dist}/bin/transactor'.format(dist=datomic_dist_dir),
        '-Xmx4G',
        '-Xms4G',
        transactor_properties_path])
    conf['watcher:datomic-transactor'] = dict(cmd=transactor_cmd)
    conf['circus']['loggerconfig'] = logger_config
    with open(conf_target_path, 'wb') as outfile:
        conf.write(outfile=outfile)
    logger.info('Starting datomic transactor via circusd')
    local('circusd --daemon ' + conf_target_path)
    time.sleep(2)
    logger.info('Started datomic transactor')


def prepare_target_db(logger,
                      pseudoace_jar_path,
                      transactor_url,
                      edn_logs_dir,
                      acedb_dump_dir,
                      java='java8'):
    cmd = ('{java} -jar {jar_path} '
           '--url {transactor_url} '
           '--acedump-dir={acedump_dir} '
           '--log-dir={edn_logs_dir} '
           '--verbose '
           'prepare-import')
    cmd = cmd.format(java=java,
                     jar_path=pseudoace_jar_path,
                     transactor_url=transactor_url,
                     acedump_dir=acedb_dump_dir,
                     edn_logs_dir=edn_logs_dir)
    logger.info('Running pseudoace command: {}', cmd)
    out = local(cmd)
    logger.info(out)


def dist_path(name):
    version = get_deploy_versions()[name]
    fqname = '{name}-{version}'.format(name=name, version=version)
    return install_path(name, fqname)


@run.command()
@option('--java-cmd', default='java8')
@click.pass_context
def setup(ctx, java_cmd):
    versions = get_deploy_versions()
    local(['wb-db-install'] + list(versions))
    data_release = versions['acedb_data']
    datomic_free_path = dist_path('datomic_free')
    acedb_data_dir = install_path('acedb_data')
    acedb_dump_dir = install_path('acedb_dump')
    edn_logs_dir = install_path('edn_logs')
    circus_ini_path = install_path('circus.ini')
    pseudoace_jar_path = dist_path('pseudoace') + '.jar'
    transactor_url = 'datomic:free://localhost:4334/' + data_release
    ctx.invoke(acedb_dump,
               dump_dir=acedb_dump_dir,
               db_directory=acedb_data_dir)
    configure_transactor(circus_ini_path, datomic_free_path)
    prepare_target_db(pseudoace_jar_path,
                      transactor_url,
                      edn_logs_dir,
                      acedb_dump_dir,
                      java=java_cmd)


def sort_edn_log_shell(path):
    logger.info('Sorting {}', path)
    pseudoace_path = dist_path('pseudoace')
    script = os.path.join(pseudoace_path, 'sort_edn_log.sh')
    cmd = ' '.join((script, path))
    logger.info('Command: {}', cmd)
    return local(cmd)


@run.command('sort-edn-logs')
def sort_edn_logs():
    gzipped_edn_logfiles = glob.glob(install_path('edn-logs', '*.edn.gz'))
    with multiprocessing.Pool() as pool:
        pool.map(sort_edn_log, gzipped_edn_logfiles, 10)


cli = run()
