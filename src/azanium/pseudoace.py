import csv
import os
import psutil

import markdown

from . import github
from . import log
from . import util


logger = log.get_logger(namespace=__name__)

gh_repo_path = 'WormBase/wormbase-pipeline'

annot_models_gh_file_path = 'wspec/models.wrm.annot'


def run_pseudoace(context, *args, **kw):
    url = context.datomic_url(db_name=kw.get('db_name'))
    cmd = [context.java_cmd,
           '-cp',
           context.pseudoace_jar_path,
           'clojure.main',
           '-m',
           'pseudoace.cli',
           '--url=' + url]
    cmd.extend(list(args))
    logger.info('Running pseudoace command: {}', ' '.join(cmd))
    out = util.local(cmd)
    logger.info(out)

def _read_annotated_models(version):
    """Read the contents of the annotated models file from github."""
    repo = github.repo_from_path(github.WB_PIPELINE_REPO)
    annot_file_content = github.read_released_file(repo,
                                                   version,
                                                   annot_models_gh_file_path)
    return annot_file_content


def source_annotated_models_file(context):
    """Sources the annotated models file from github into a local file.

    Returns the local filename. """
    target_dir = context.base_path
    release_tag = util.ws_release_tag()
    annot_file_content = _read_annotated_models(release_tag)
    am_local_filename = os.path.basename(annot_models_gh_file_path) + '.' + release_tag
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


def apply_patches(context):
    patches_ftp_url = '{}/acedb/PATCHES'.format(util.get_ftp_url())
    run_pseudoace(context,
                  '--patches-ftp-url=' + patches_ftp_url,
                  '--verbose',
                  'apply-patches')


def qa_report(context, acedb_id_catalog_path):
    data_release = util.get_data_release_version()
    report_filename = 'all_classes_report.{}.txt'.format(data_release)
    report_path = os.path.join(acedb_id_catalog_path, report_filename)
    out_path = os.path.join(
        context.base_path,
        '{release}-report.csv'.format(release=data_release))
    run_pseudoace(context,
                  '--acedb-class-report=' + report_path,
                  '--report-filename=' + out_path,
                  'generate-report')
    return out_path


def homol_import(context):
    am_filename = source_annotated_models_file(context)
    acedump_dir = context.path('acedb-dump')
    models_path = os.path.join(context.path('acedb_database'),
                               'wspec',
                               am_filename)
    homol_logs_dir = context.path('homol-edn-logs')
    log_dir = context.path('edn-logs')
    os.makedirs(homol_logs_dir, exist_ok=True)
    run_pseudoace(context,
                  '--models-filename=' + models_path,
                  '--acedump-dir=' + acedump_dir,
                  '--log-dir=' + log_dir,
                  '--homol-log-dir=' + homol_logs_dir,
                  '--verbose=true',
                  'homol-import',
                  db_name='homol')


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
