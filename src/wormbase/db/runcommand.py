import functools
import multiprocessing
import os
import time


import click
from configobj import ConfigObj
from pkg_resources import resource_filename

from .logging import get_logger
from .logging import setup_logging
from .util import echo_sig
from .util import echo_waiting
from .util import get_deploy_versions
from .util import local
from .util import log_level_option
from .util import option


logger = get_logger(__name__, verbose=True)

eu = os.path.expanduser

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
    local('tace ' + db_directory, stdin=dump_cmd)
    logger.info('Dumped ACeDB files to {}', dump_dir)


def configure_transactor(logger, conf_target_path, datomic_dist_dir):
    path = resource_filename(
        __package__,
        'cloud-config/circus-datomic-free-transactor.ini.template')
    transactor_properties_path = resource_filename(
        __package__,
        'cloud-config/datomic-free-transactor.ini')
    logger_config = resource_filename(
        __package__,
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
    echo_waiting('Waiting for transactor to start ... ')
    local('circusd --daemon ' + conf_target_path)
    time.sleep(3)
    echo_sig('done')
    logger.info('Started datomic transactor')


def prepare_target_db(logger,
                      psuedoace_jar_path,
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
                     jar_path=psuedoace_jar_path,
                     transactor_url=transactor_url,
                     acedump_dir=acedb_dump_dir,
                     edn_logs_dir=edn_logs_dir)
    logger.info('Running pseudoace command: {}', cmd)
    out = local(cmd)
    logger.info(out)


def dist_path(name):
    version = get_deploy_versions()[name]
    path = '~/{name}/{name}-{version}'.format(name=name,
                                              version=version)
    return os.path.expanduser(path)


@run.command()
@option('--java-cmd', default='java8')
@click.pass_context
def setup(ctx, java_cmd):
    versions = get_deploy_versions()
    local(['wb-db-install'] + list(versions))
    data_release = versions['acedb_data']
    datomic_free_path = dist_path('datomic_free')
    acedb_dump_dir = eu('~/acedb_dump')
    edn_logs_dir = eu('~/edn_logs')
    circus_ini_path = eu('~/circus.ini')
    psuedoace_jar_path = dist_path('psuedoace') + '.jar'
    transactor_url = 'datomic:free://localhost:4334/' + data_release
    ctx.invoke(acedb_dump, dump_dir=acedb_dump_dir)
    configure_transactor(circus_ini_path, datomic_free_path)
    prepare_target_db(psuedoace_jar_path,
                      transactor_url,
                      edn_logs_dir,
                      acedb_dump_dir,
                      java=java_cmd)


@run.command()
def sort_edn_logs():
    pseudoace_path = dist_path('pseudoace')
    script_path = os.path.join(pseudoace_path, 'sort_edn_log.sh')
    edn_logs_dir = eu('~/edn_logs')
    fn = functools.partial(local, script_path)
    n_cpus = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(n_cpus)
    pool.map(fn, os.listdir(edn_logs_dir))


cli = run()
