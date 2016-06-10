import time

from configobj import ConfigObj

from . import util


def backup_db(context, db, logger):
    from_uri = context.datomic_url(db)
    to_uri = 's3://wb-datomic-backups/' + db
    cmd = ['bin/datomic'] + list(util.jvm_mem_opts(0.20)) + [from_uri, to_uri]
    cwd = util.install_path('datomic_free')
    logger.info('Backing up {} {}', from_uri, to_uri)
    util.local(cmd, cwd=cwd)
    logger.info('Backup complete')


def configure_transactor(context, logger):
    circus_ini_template_path = util.pkgpath(
        'cloud-config/circus-datomic-free-transactor.ini.template')
    transactor_properties_path = util.pkgpath(
        'cloud-config/datomic-free-transactor.ini')
    logger_config = util.pkgpath(
        'cloud-config/circus-logging-config.yaml')
    with open(circus_ini_template_path) as infile:
        conf = ConfigObj(infile=infile)
    datomic_path = context.datomic_path
    transactor_cmd = ['{}/bin/transactor'.format(dist=datomic_path)]
    transactor_cmd.extend(util.jvm_mem_opts(0.20))
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
