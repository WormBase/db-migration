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

from . import github
from . import notifications
from . import root_command
from .log import get_logger
from .util import download
from .util import ftp_download
from .util import get_deploy_versions
from .util import local
from .util import make_executable
from .util import option
from .util import pass_command_context
from .util import touch_dir

logger = get_logger(__name__)

Meta = collections.namedtuple('Meta', ('download_dir',
                                       'install_dir',
                                       'version'))

DEFAULT_EBI_FTP_PATH_PREFIX = '/pub/databases/wormbase/staging/releases'

def installer(func):
    """Decorate a click command as an ``installer``.

    Adds installer information to the click context object which
    is in turn passed to the decoratee command function.

    Wraps the command function in a function for result chaining.
    """
    @pass_command_context
    def cmd_proxy(cmd_ctx, *args, **kw):
        f_name = func.__name__
        tmpdir = tempfile.mkdtemp(suffix='-db-migration-downloads')
        download_dir = os.path.join(tmpdir, f_name)
        install_dir = cmd_ctx.path(f_name)
        version = get_deploy_versions()[f_name]
        for path in (download_dir, install_dir):
            os.makedirs(path, exist_ok=True)
        meta = Meta(download_dir=download_dir,
                    install_dir=install_dir,
                    version=version)
        ctx = click.get_current_context()
        return ctx.invoke(func, meta, *args[1:], **kw)

    def command_proxy(*args, **kw):
        return functools.partial(cmd_proxy, *args, **kw)

    return functools.update_wrapper(command_proxy, func)


@root_command.group(chain=True, invoke_without_command=True)
@pass_command_context
def install(ctx):
    """Software installers for the WormBase database migration.

    All software will be installed under a common base path,
    as specified to the parent command.
    """


@install.resultcallback()
def pipeline(installers):
    for install_command in installers:
        install_command()


@install.command(short_help='Installs the ACeDB ID catalog for QA report.')
@option('--ftp-host',
        default='ftp.ebi.ac.uk',
        help='FTP hostname for ACeDB data.')
@option('--remote-path-template',
        default=DEFAULT_EBI_FTP_PATH_PREFIX + '/{version}/REPORTS',
        help='Path to the file(s) containing compressed database.')
@option('--file-selector-regexp',
        default='all_classes_report.{version}\.txt\.gz$',
        help='File selection regexp')
@installer
def acedb_id_catalog(meta,
                     ftp_host,
                     remote_path_template,
                     file_selector_regexp):
    """Installs the ACeDB id catalog use by QA report generation."""
    format_path = remote_path_template.format
    file_selector_regexp = file_selector_regexp.format(version=meta.version)
    downloaded = ftp_download(ftp_host,
                              file_selector_regexp,
                              meta.download_dir,
                              logger,
                              initial_cwd=format_path(version=meta.version))
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


@install.command(short_help='Installs the ACeDB database.')
@option('--ftp-host',
        default='ftp.ebi.ac.uk',
        help='FTP hostname for ACeDB data.')
@option('--remote-path-template',
        default=DEFAULT_EBI_FTP_PATH_PREFIX + '/{version}/acedb',
        help='Path to the file(s) containing compressed database.')
@option('--file-selector-regexp',
        default='.*\.tar\.gz$',
        help='File selection regexp')
@installer
def acedb_database(meta,
                   ftp_host,
                   remote_path_template,
                   file_selector_regexp):
    """Installs the ACeDB database system."""
    format_path = remote_path_template.format
    version = meta.version
    wspec_dir = os.path.join(meta.install_dir, 'wspec')
    ftp_get = functools.partial(ftp_download,
                                logger=logger,
                                initial_cwd=format_path(version=version))
    downloaded = ftp_get(ftp_host, file_selector_regexp, meta.download_dir)
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
    touch_dir(meta.install_dir)
    return meta.install_dir


@install.command(short_help='Installs the ACeDB "tace" binary')
@option('-t', '--url-template',
        default=('ftp://ftp.sanger.ac.uk/pub/acedb/MONTHLY/'
                 'ACEDB-binaryLINUX_{version}.tar.gz'),
        help='URL for versioned ACeDB binaries')
@installer
def tace(meta, url_template):
    """Installs the ACeDB "tace" binary program."""
    version = meta.version
    url = url_template.format(version=version)
    pr = urllib.parse.urlparse(url)
    downloaded = ftp_download(pr.netloc,
                              os.path.basename(pr.path),
                              meta.download_dir,
                              logger,
                              initial_cwd=os.path.dirname(pr.path))
    local_path = downloaded[0]
    with tarfile.open(local_path) as tf:
        tf.extract('./tace', path=meta.install_dir)
    tace_path = os.path.join(meta.install_dir, 'tace')
    touch_dir(meta.install_dir)
    make_executable(tace_path, logger)
    return tace_path


@install.command(short_help='Installs datomic-free')
@option('-t', '--url-template',
        default='https://my.datomic.com/downloads/free/{version}',
        help='URL template for Datomic Free version')
@installer
def datomic_free(meta, url_template):
    """Installs Datomic (free version)."""
    install_dir = meta.install_dir
    version = meta.version
    url = url_template.format(version=version)
    fullname = 'datomic-free-{version}'.format(version=version)
    local_filename = fullname + '.zip'
    download_path = os.path.join(meta.download_dir, local_filename)
    logger.info('Downloading and extracting {} to {}', fullname, install_dir)
    tmpdir = tempfile.mkdtemp()
    with zipfile.ZipFile(download(url, download_path)) as zf:
        zf.extractall(tmpdir)
    os.rmdir(install_dir)
    shutil.move(os.path.join(tmpdir, fullname), install_dir)
    touch_dir(install_dir)
    logger.info('Installed {} into {}', fullname, install_dir)
    logger.info('Setting environment variable DATOMIC_HOME={}', install_dir)
    bin_dir = os.path.join(install_dir, 'bin')
    for filename in os.listdir(bin_dir):
        bin_path = os.path.join(bin_dir, filename)
        make_executable(bin_path, logger, symlink_dir=None)
    os.chdir(install_dir)
    mvn_install = os.path.join('bin', 'maven-install')
    logger.info('Installing datomic via {}', os.path.abspath(mvn_install))
    mvn_install_out = local(mvn_install)
    logger.info('Installed datomic_free')
    logger.debug(mvn_install_out)
    return install_dir


@install.command(short_help='Installs pseudoace')
@installer
def pseudoace(meta):
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
    touch_dir(install_dir)
    logger.info('Extracted {} to {}', archive_filename, install_dir)
    return install_dir


@install.command('all', short_help='Installs everything')
@pass_command_context
def all(context):
    """Installs all software and data."""
    # Invoke all commands via the install group command chain.
    # This has the same effect as if run on command line, e.g:
    # azanium install dataomic_free pseudoace acedb_database ..
    ctx = click.get_current_context()
    install_cmd_names = sorted(context.versions)
    orig_protected_args = ctx.protected_args[:]
    ctx.protected_args.extend(install_cmd_names)
    try:
        install.invoke(ctx)
    finally:
        ctx.protected_args[:] = orig_protected_args
    attachments = []
    for name in install_cmd_names:
        version = context.versions[name]
        title = 'Installed {} (version: {})'.format(name, version)
        ts = os.path.getmtime(context.path(name))
        attachment = notifications.Attachment(title, ts=ts)
        attachments.append(attachment)
    return attachments
