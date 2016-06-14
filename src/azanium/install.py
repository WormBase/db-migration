import collections
import contextlib
import ftplib
import functools
import getpass
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
from . import root_command
from .log import get_logger
from .util import download
from .util import get_deploy_versions
from .util import local
from .util import option
from .util import pass_ec2_command_context


logger = get_logger(__name__)

Meta = collections.namedtuple('Meta', ('download_dir',
                                       'install_dir',
                                       'version'))


def _make_executable(path, logger, mode=0o775, symlink_to_local_bin=False):
    logger.info('Setting permissions on {} to {}',
                path,
                stat.filemode(mode))
    os.chmod(path, mode)
    if symlink_to_local_bin:
        bin_dirname = os.path.expanduser('~/.local/bin')
        bin_filename = os.path.basename(path)
        bin_path = os.path.join(bin_dirname, bin_filename)
        if os.path.islink(bin_path):
            os.unlink(bin_path)
        os.symlink(path, bin_path)
        logger.debug('Created symlink from {} to {}', path, bin_path)


@contextlib.contextmanager
def _ftp(host):
    ftp = ftplib.FTP(host=host, user='anonymous')
    ftp.set_pasv(True)
    yield ftp
    ftp.quit()


def installer(func):
    """Decorate a click command as an ``installer``.

    Adds installer information to the click context object which
    is in turn passed to the decoratee command function.

    Wraps the command function in a function for result chaining.
    """
    @pass_ec2_command_context
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


@root_command.group(chain=True, invoke_without_command=False)
@click.pass_context
def install(ctx):
    """Software installers for the WormBase database migration.

    All software will be installed under a common path:

       /datastore/wormbase
    """


@install.resultcallback()
def pipeline(installers):
    for install_command in installers:
        install_command()


@install.command(short_help='Install ACeDB.')
@option('--ftp-host',
        default='ftp.ebi.ac.uk',
        help='FTP hostname for ACeDB data.')
@option('--remote-path-template',
        default='pub/databases/wormbase/releases/{version}/acedb',
        help='Path to the file(s) containing compressed database.')
@option('--file-selector-regexp',
        default='.*\.tar\.gz$',
        help='File selection regexp')
@installer
def acedb_database(meta,
                   ftp_host,
                   remote_path_template,
                   file_selector_regexp):
    """Install ACeDB."""
    download_dir = meta.download_dir
    install_dir = meta.install_dir
    format_path = remote_path_template.format
    file_selector = functools.partial(re.match, file_selector_regexp)
    version = meta.version
    logger.info('Connecting to {}', ftp_host)
    with _ftp(ftp_host) as ftp:
        ftp.cwd(format_path(version=version))
        filenames = filter(file_selector, ftp.nlst('.'))
        for filename in filenames:
            out_path = os.path.join(download_dir, filename)
            logger.info('Saving {} to {}', filename, out_path)
            with open(out_path, 'wb') as fp:
                ftp.retrbinary('RETR ' + filename, fp.write)
            with tarfile.open(fp.name) as tf:
                logger.info('Extracting {} to {}', fp.name, install_dir)
                tf.extractall(path=install_dir)
    # Enable the Dump command
    passwd_path = os.path.join(install_dir, 'wspec', 'passwd.wrm')
    mode = 0o644
    logger.info('Changing permissions of {} to {}',
                passwd_path,
                stat.filemode(mode))
    os.chmod(passwd_path, mode)
    username = getpass.getuser()
    with open(passwd_path, 'a') as fp:
        logger.info('Adding {} to {}', username, passwd_path)
        fp.write(username + os.linesep)


@install.command(short_help='Install the ACeDB "tace" binary')
@option('-t', '--url-template',
        default=('ftp://ftp.sanger.ac.uk/pub/acedb/MONTHLY/'
                 'ACEDB-binaryLINUX_{version}.tar.gz'),
        help='URL for versioned ACeDB binaries')
@installer
def tace(meta, url_template):
    """Install the ACeDB "tace" binary program."""
    install_dir = meta.install_dir
    download_dir = meta.download_dir
    version = meta.version
    url = url_template.format(version=version)
    pr = urllib.parse.urlparse(url)
    with _ftp(pr.netloc) as ftp:
        ftp.cwd(os.path.dirname(pr.path))
        filename = os.path.basename(pr.path)
        local_filename = os.path.join(download_dir, os.path.basename(pr.path))
        with open(local_filename, 'wb') as fp:
            logger.info('Downloading {}', filename)
            ftp.retrbinary('RETR ' + filename, fp.write)
    with tarfile.open(local_filename) as tf:
        tf.extract('./tace', path=install_dir)
    _make_executable(os.path.join(install_dir, 'tace'),
                     logger,
                     symlink_to_local_bin=True)


@install.command(short_help='Install datomic-free')
@option('-t', '--url-template',
        default='https://my.datomic.com/downloads/free/{version}',
        help='URL template for Datomic Free version')
@installer
def datomic_free(meta, url_template):
    """Install Datomic (free version)."""
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
    os.rmdir(tmpdir)
    logger.info('Installed {} into {}', fullname, install_dir)
    logger.info('Setting environment variable DATOMIC_HOME={}', install_dir)
    bin_dir = os.path.join(install_dir, 'bin')
    for filename in os.listdir(bin_dir):
        bin_path = os.path.join(bin_dir, filename)
        _make_executable(bin_path, logger)
    os.chdir(install_dir)
    mvn_install = os.path.join('bin', 'maven-install')
    logger.info('Installing datomic via {}', os.path.abspath(mvn_install))
    mvn_install_out = local(mvn_install)
    logger.info('Installed datomic_free')
    logger.debug(mvn_install_out)


@install.command(short_help='Install pseudoace')
@installer
def pseudoace(meta):
    """Install pseudoace."""
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
    fullname = 'pseudoace-' + tag
    tmp_src_path = os.path.join(tempdir, fullname)
    src_path = tmp_src_path.rstrip('-' + tag)
    os.rename(tmp_src_path, src_path)
    shutil.rmtree(install_dir)
    shutil.move(src_path, install_dir)
    logger.info('Extracted pseudoace-{} to {}', tag, install_dir)
