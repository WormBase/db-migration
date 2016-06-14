import os
import psutil

from . import util


def run_pseudoace(logger, context, *args):
    cmd = [context.java_cmd,
           '-jar', context.pseudoace_jar_path,
           '--url=' + context.datomic_url()]
    cmd.extend(list(args))
    logger.info('Running pseudoace command: {}', ' '.join(cmd))
    out = util.local(cmd)
    logger.info(out)


def prepare_target_db(context, edn_logs_dir, acedb_dump_dir, logger):
    run_pseudoace(logger,
                  context,
                  '--acedump-dir=' + acedb_dump_dir,
                  '--log-dir=' + edn_logs_dir,
                  '--verbose',
                  'prepare-import')


def sort_edn_logs(context, logger):
    pseudoace_path = context.path('pseudoace')
    script_path = os.path.join(pseudoace_path, 'sort_edn_log.sh')
    edn_logs_dir = context.path('edn-logs')
    n_procs = str(psutil.cpu_count())
    cmd = ['find', edn_logs_dir, '-type', 'f', '-name', '"*.edn.gz"']
    cmd.extend(['|', 'xargs', '-n', '1', '-P', n_procs, script_path])
    logger.info('Sorting EDN logs')
    util.local(cmd)
    logger.info('Finished sorting EDN logs')


def import_logs(context, edn_logs_dir, logger):
    run_pseudoace(logger,
                  context,
                  '--log-dir=' + edn_logs_dir,
                  '--verbose',
                  'import-logs')


def qa_report(context, logger):
    data_release = context.data_release_version
    ref_build_data_path = context.path('ref-build-data')
    out_path = os.path.expanduser(
        '~/{data_release}-report.txt'.format(data_relase=data_release))
    run_pseudoace(logger,
                  context,
                  '--build-data=' + ref_build_data_path,
                  '--report-filename=' + out_path,
                  'generate-report')
