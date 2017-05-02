import os
import psutil

import markdown

from . import log
from . import util


logger = log.get_logger(namespace=__name__)


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
    fn_template = 'models.wrm.{.data_release_version}.annot'
    ann_models_filename = fn_template.format(context)
    models_path = os.path.join(context.path('acedb_database'),
                               'wspec',
                               ann_models_filename)
    run_pseudoace(context,
                  '--models-filename',
                  models_path,
                  '--verbose',
                  'create-database')


def acedb_dump_to_edn_logs(context, acedb_dump_dir, edn_logs_dir):
    logger.info('Convering ACeDB files to EDN logs')
    os.makedirs(edn_logs_dir, exist_ok=True)
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
    script_path = os.path.join(pseudoace_path, 'sort-edn-log.sh')
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
    build_data_filename = 'all_classes_report.{}.txt'.format(data_release)
    build_data_path = os.path.join(acedb_id_catalog_path, build_data_filename)
    out_path = os.path.expanduser(
        '~/{release}-report.txt'.format(release=data_release))
    run_pseudoace(context,
                  '--build-data=' + build_data_path,
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

def excise_tmp_data(context):
    run_pseudoace(context, 'excise-tmp-data', '--verbose')
