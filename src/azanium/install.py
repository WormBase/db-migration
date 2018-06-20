import collections
import functools
import getpass
import gzip
import os
import re
import shutil
import stat
import tarfile
import tempfile
import urllib.parse
import zipfile


import click

from . import config
from . import github
from . import log
from . import notifications
from . import root_command
from . import util

logger = log.get_logger(__name__)

Meta = collections.namedtuple('Meta', ('download_dir',
                                       'install_dir',
                                       'version',
                                       'context'))

def preliminary_checks():
    # check github release of wb pipeline is done
    # check that the az configuration file is present
    # warn if slack notifications are not to be sent (not configured)
    conf = config.parse()
    if not conf:
        msg = __package__ + ' has not been configured.'
        util.echo_error(msg)
        raise click.Abort(msg)
    ws_release_version = util.get_data_release_version()
    if not ws_release_version:
        msg = 'azanium configure has not been run'
        raise click.Abort(msg)
    if not github.is_released(ws_release_version):
        msg  = 'The wormbase-pipeline repo has not been tagged on github'
        raise click.Abort(msg)
    if notifications.__name__ not in conf:
        logger.warn('Slack notifications are not enabled -'
                    'integration has been disabled')
        logger.warn('It is safe to re-run the "azanium configure" command ' 
                    'after the current command exits, should you wish to '
                    'enable notifications')


def mk_meta(cmd_ctx, func):
    f_name = func.__name__
    tmpdir = tempfile.mkdtemp(suffix='-db-migration-downloads')
    download_dir = os.path.join(tmpdir, f_name)
    install_dir = cmd_ctx.path(f_name)
    version = util.get_deploy_versions()[f_name]
    for path in (download_dir, install_dir):
        os.makedirs(path, exist_ok=True)
        meta = Meta(download_dir=download_dir,
                    install_dir=install_dir,
                    version=version,
                    context=cmd_ctx)
    return meta


def installer(func):
    """Decorate a click command as an ``installer``.

    Adds installer information to the click context object which
    is in turn passed to the decoratee command function.

    Wraps the command function in a function for result chaining.
    """
    @util.pass_command_context
    def cmd_proxy(cmd_ctx, *args, **kw):
        preliminary_checks()
        ctx = click.get_current_context()
        meta = mk_meta(cmd_ctx, func)
        return ctx.invoke(func, meta, *args[1:], **kw)

    def command_proxy(*args, **kw):
        return functools.partial(cmd_proxy, *args, **kw)

    return functools.update_wrapper(command_proxy, func)


@root_command.group(chain=True, invoke_without_command=True)
@util.pass_command_context
def installers(ctx):
    """Software installers for the WormBase database migration.

    All software will be installed under a common base path,
    as specified to the parent command.
    """

@installers.resultcallback()
def pipeline(installers, *args, **kw):
    for install_command in installers:
        install_command(*args, **kw)

def acedb_id_catalog(
        meta,
        report_file_regexp='all_classes_report.{version}\.txt\.gz$'):
    """Installs the ACeDB id catalog use by QA report generation."""
    (host, path, version) = util.split_ftp_url(util.get_ftp_url())
    cwd = os.path.join(path, 'REPORTS')
    regexp = 'all_classes_report\.{}\.txt\.gz$'.format(version)
    downloaded = util.ftp_download(host,
                                   regexp,
                                   meta.download_dir,
                                   logger,
                                   initial_cwd=cwd)

    downloaded_path = downloaded[0]
    with gzip.open(downloaded_path) as gz_fp:
        filename = re.sub('^(?P<fn>.*)\.gz',
                          '\g<fn>',
                          os.path.basename(downloaded_path))
        out_path = os.path.join(meta.install_dir, filename)
        with open(out_path, 'wb') as fp:
            logger.info('Writing {}', fp.name)
            fp.write(gz_fp.read())
        return fp.name


@installers.command(short_help='Installs the ACeDB database.')
@util.option('--file-selector-regexp',
             default='.*\.tar\.gz$',
             help='File selection regexp')
@installer
def acedb_database(meta, file_selector_regexp):
    """Installs the ACeDB database system."""
    ctx = click.get_current_context()
    ftp_url = util.get_ftp_url()
    ctx.invoke(acedb_id_catalog, mk_meta(meta.context, acedb_id_catalog), ftp_url)
    (host, path, version) = util.split_ftp_url(ftp_url)
    cwd = os.path.join(path, 'acedb')
    wspec_dir = os.path.join(meta.install_dir, 'wspec')
    ftp_get = functools.partial(util.ftp_download,
                                logger=logger,
                                initial_cwd=cwd)
    downloaded = ftp_get(host, file_selector_regexp, meta.download_dir)
    for path in downloaded:
        with tarfile.open(path) as tf:
            logger.info('Extracting {} to {}', path, meta.install_dir)
            tf.extractall(path=meta.install_dir)

    # Enable the Dump command (requires adding user to ACeDB pw file)
    passwd_path = os.path.join(wspec_dir, 'passwd.wrm')
    mode = 0o644
    logger.info('Changing permissions of {} to {}',
                passwd_path,
                stat.filemode(mode))
    os.chmod(passwd_path, mode)
    username = getpass.getuser()
    with open(passwd_path, 'a') as fp:
        logger.info('Adding {} to {}', username, passwd_path)
        fp.write(username + os.linesep)
    util.touch_dir(meta.install_dir)
    return meta.install_dir


@installers.command(short_help='Installs the ACeDB "tace" binary')
@util.option('-t', '--url-template',
             default=('ftp://ftp.sanger.ac.uk/pub/acedb/MONTHLY/'
                      'ACEDB-binaryLINUX_{version}.tar.gz'),
             help='URL for versioned ACeDB binaries')
@installer
def tace(meta, url_template=None):
    """Installs the ACeDB "tace" binary program."""
    version = meta.version
    url = url_template.format(version=version)
    pr = urllib.parse.urlparse(url)
    downloaded = util.ftp_download(pr.netloc,
                                   os.path.basename(pr.path),
                                   meta.download_dir,
                                   logger,
                                   initial_cwd=os.path.dirname(pr.path))
    local_path = downloaded[0]
    with tarfile.open(local_path) as tf:
        tf.extract('./tace', path=meta.install_dir)
    tace_path = os.path.join(meta.install_dir, 'tace')
    util.touch_dir(meta.install_dir)
    util.make_executable(tace_path, logger)
    return tace_path


@installers.command(short_help='Installs datomic-free')
@util.option('-t', '--url-template',
             default='https://my.datomic.com/downloads/free/{version}',
             help='URL template for Datomic Free version')
@installer
def datomic_free(meta, url_template=None):
    """Installs Datomic (free version)."""
    install_dir = meta.install_dir
    version = meta.version
    url = url_template.format(version=version)
    fullname = 'datomic-free-{version}'.format(version=version)
    local_filename = fullname + '.zip'
    download_path = os.path.join(meta.download_dir, local_filename)
    logger.info('Downloading and extracting {} to {}', fullname, install_dir)
    tmpdir = tempfile.mkdtemp()
    with zipfile.ZipFile(util.download(url, download_path)) as zf:
        zf.extractall(tmpdir)
    os.rmdir(install_dir)
    shutil.move(os.path.join(tmpdir, fullname), install_dir)
    util.touch_dir(install_dir)
    logger.info('Installed {} into {}', fullname, install_dir)
    logger.info('Setting environment variable DATOMIC_HOME={}', install_dir)
    bin_dir = os.path.join(install_dir, 'bin')
    for filename in os.listdir(bin_dir):
        bin_path = os.path.join(bin_dir, filename)
        util.make_executable(bin_path, logger, symlink_dir=None)
    os.chdir(install_dir)
    mvn_install = os.path.join('bin', 'maven-install')
    logger.info('Installing datomic via {}', os.path.abspath(mvn_install))
    mvn_install_out = util.local(mvn_install)
    logger.info('Installed datomic_free')
    logger.debug(mvn_install_out)
    return install_dir


@installers.command(short_help='Installs pseudoace')
@installer
def pseudoace(meta, **kw):
    """Installs pseudoace."""
    download_dir = meta.download_dir
    install_dir = meta.install_dir
    tag = meta.version
    logger.info('Downloading pseudoace release {} from github', tag)
    dl_path = github.download_release_binary(
        'WormBase/pseudoace',
        tag,
        to_directory=download_dir)
    tempdir = tempfile.mkdtemp()
    with tarfile.open(dl_path) as tf:
        tf.extractall(path=tempdir)
    archive_filename = os.path.split(dl_path)[-1]
    fullname = archive_filename.rsplit('.', 2)[0]
    tmp_src_path = os.path.join(tempdir, fullname)
    src_path = tmp_src_path.rstrip('-' + tag)
    os.rename(tmp_src_path, src_path)
    shutil.rmtree(install_dir)
    shutil.move(src_path, install_dir)
    util.touch_dir(install_dir)
    logger.info('Extracted {} to {}', archive_filename, install_dir)
    return install_dir


@root_command.command('install', short_help='Installs everything')
@util.pass_command_context
def install(context):
    """Installs all software and data."""
    # Invoke all commands via the install group command chain.
    # This has the same effect as if run on command line, e.g:
    # azanium install dataomic_free pseudoace acedb_database ..
    preliminary_checks()
    ctx = click.get_current_context()
    install_cmd_names = sorted(installers.commands)
    orig_protected_args = ctx.protected_args[:]
    ctx.protected_args.extend(install_cmd_names)
    try:
        installers.invoke(ctx)
    finally:
        ctx.protected_args[:] = orig_protected_args
    attachments = []
    versions = util.get_deploy_versions()
    for name in install_cmd_names:
        version = versions[name]
        title = 'Installed {} (version: {})'.format(name, version)
        ts = os.path.getmtime(context.path(name))
        attachment = notifications.Attachment(title, ts=ts)
        attachments.append(attachment)
    return attachments
