import logging
import os
import psutil

import markdown

from . import util


logger = logging.getLogger(__name__)


def run_pseudoace(context, *args):
    cmd = [context.java_cmd,
           '-jar', context.pseudoace_jar_path,
           '--url=' + context.datomic_url()]
    cmd.extend(list(args))
    logger.info('Running pseudoace command: {}', ' '.join(cmd))
    out = util.local(cmd)
    logger.info(out)


def create_database(context):
    logger.info('Creating datomic database')
    run_pseudoace(context, '-v', 'create-database')


def acedb_dump_to_edn_logs(context, acedb_dump_dir, edn_logs_dir):
    logger.info('Convering ACeDB files to EDN logs')
    run_pseudoace(context,
                  '--acedump-dir=' + acedb_dump_dir,
                  '--log-dir=' + edn_logs_dir,
                  '--verbose',
                  'acedump-to-edn-logs')


def prepare_target_db(context, edn_logs_dir, acedb_dump_dir):
    run_pseudoace(context,
                  '--acedump-dir=' + acedb_dump_dir,
                  '--log-dir=' + edn_logs_dir,
                  '--verbose',
                  'prepare-import')


def sort_edn_logs(context, edn_logs_dir):
    pseudoace_path = context.path('pseudoace')
    script_path = os.path.join(pseudoace_path, 'sort_edn_log.sh')
    n_procs = str(psutil.cpu_count())
    cmd = ['find', edn_logs_dir, '-type', 'f', '-name', '"*.edn.gz"']
    cmd.extend(['|', 'xargs', '-n', '1', '-P', n_procs, script_path])
    logger.info('Sorting EDN logs')
    util.local(cmd)
    logger.info('Finished sorting EDN logs')


def import_logs(context, edn_logs_dir):
    run_pseudoace(context,
                  '--log-dir=' + edn_logs_dir,
                  '--verbose',
                  'import-logs')


def qa_report(context, acedb_id_catalog_path):
    data_release = context.data_release_version
    out_path = os.path.expanduser(
        '~/{data_release}-report.txt'.format(data_relase=data_release))
    run_pseudoace(context,
                  '--build-data=' + acedb_id_catalog_path,
                  '--report-filename=' + out_path,
                  'generate-report')
    return out_path


def qa_report_to_html(report_path, title):
    with open(report_path) as fp:
        report_matrix = list(line.strip().split() for line in fp)
    md_table = util.markdown_table(report_matrix)
    html_report = '<html><body><h1>{title}</h1>'.format(title=title)
    html_report += markdown.markdown(md_table, ['markdown.extensions.extra'])
    html_report += '</body></html>'
    return html_report
