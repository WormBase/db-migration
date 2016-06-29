import datetime
import time

from configobj import ConfigObj

from . import log
from . import util


logger = log.get_logger(namespace=__name__)


def backup_db(context, db):
    from_uri = context.datomic_url(db)
    date_stamp = datetime.date.today().isoformat()
    to_uri = 's3://wormbase/db-migration/{}/{}'.format(date_stamp, db)
    cmd = ['bin/datomic',
           util.jvm_mem_opts(0.20),
           'backup-db',
           from_uri,
           to_uri]
    cwd = context.path('datomic_free')
    logger.info('Backing up database {} to {}', from_uri, to_uri)
    util.local(cmd, cwd=cwd)
    logger.info('Database backup complete')
    return to_uri


def configure_transactor(context, datomic_path):
    circus_ini_template_path = util.pkgpath(
        'cloud-config/circus-datomic-free-transactor.ini.template')
    transactor_properties_path = util.pkgpath(
        'cloud-config/datomic-free-transactor.ini')
    logger_config = util.pkgpath(
        'cloud-config/circus-logging-config.yaml')
    with open(circus_ini_template_path) as infile:
        conf = ConfigObj(infile=infile)
    transactor_cmd = ['{dist}/bin/transactor'.format(dist=datomic_path)]
    transactor_cmd.append(util.jvm_mem_opts(0.20))
    transactor_cmd.append(transactor_properties_path)
    conf['env:datomic-transactor'] = dict(JAVA_CMD=context.java_cmd)
    conf['watcher:datomic-transactor'] = dict(cmd=' '.join(transactor_cmd))
    conf['circus']['loggerconfig'] = logger_config
    circus_ini_path = context.path('circus.ini')
    with open(circus_ini_path, 'wb') as outfile:
        conf.write(outfile=outfile)
    logger.info('Starting datomic transactor via circusd')
    util.local('circusd --daemon ' + circus_ini_path)
    time.sleep(2)
    logger.info('Started datomic transactor')
