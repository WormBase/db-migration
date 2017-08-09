import csv
import os
import psutil

import markdown

from . import github
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


def source_annotated_models_file(context):
    """Sources the annotated models file from github.

    Returns the local filename. """
    # Get the annotated models file separately from github.
    gh_repo_path = 'WormBase/wormbase-pipeline'
    gh_file_path = 'wspec/models.wrm.annot'
    annot_file_content = github.read_released_file(gh_repo_path,
                                                   gh_file_path)
    version = context.data_release_version
    target_dir = context.base_path
    am_local_filename = os.path.basename(gh_file_path) + '.' + version
    am_local_path = os.path.join(target_dir, am_local_filename)
    with open(am_local_path, mode='wb') as fp:
        fp.write(annot_file_content)
    return fp.name


def create_database(context):
    logger.info('Creating datomic database')
    am_filename = source_annotated_models_file(context)
    models_path = os.path.join(context.path('acedb_database'),
                               'wspec',
                               am_filename)
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
    report_filename = 'all_classes_report.{}.txt'.format(data_release)
    report_path = os.path.join(acedb_id_catalog_path, report_filename)
    out_path = os.path.expanduser(
        '~/{release}-report.csv'.format(release=data_release))
    run_pseudoace(context,
                  '--acedb-class-report=' + report_path,
                  '--report-filename=' + out_path,
                  'generate-report')
    return out_path


class QADialect(csv.excel):
    quoting = csv.QUOTE_ALL


def qa_report_to_html(report_path, title):
    with open(report_path) as fp:
        report_matrix = list(csv.reader(fp, dialect=QADialect()))
    md_table = util.markdown_table(report_matrix)
    html_report = '<html><body><h1>{title}</h1>'.format(title=title)
    html_report += markdown.markdown(md_table, ['markdown.extensions.extra'])
    html_report += '</body></html>'
    return html_report

def excise_tmp_data(context):
    run_pseudoace(context, 'excise-tmp-data', '--verbose')
