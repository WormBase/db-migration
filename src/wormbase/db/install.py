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
from .logging import get_logger
from .logging import setup_logging
from .util import download
from .util import get_deploy_versions
from .util import local
from .util import log_level_option
from .util import option


logger = get_logger(__name__)

Meta = collections.namedtuple('Meta', ('download_dir',
                                       'install_dir',
                                       'version'))


def _make_executable(path, logger, mode=0o775):
    logger.info('Setting permissions on {} to {}',
                path,
                stat.filemode(mode))
    os.chmod(path, mode)
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


def persists_env(shell_init_file='~/.bashrc'):
    """Decorator for a `install` command.

    Changes to the existing environment after the
    decorated function  has been called will be
    appended to current user's shell profile.
    """
    def env_updater(func):
        def cmd_proxy(*args, **kw):
            env_before = set(os.environ.items())
            rv = func(*args, **kw)
            env_after = set(os.environ.items())
            env_vars = dict(env_after - env_before)
            if env_vars:
                path = os.path.expanduser(shell_init_file)
                with open(path, 'a') as fp:
                    for (env_var, val) in sorted(env_vars.items()):
                        new_line = 'export {var}="{val}"'
                        new_line = new_line.format(var=env_var, val=val)
                        fp.write(os.linesep.join([new_line]))
                        fp.write(os.linesep)
            return rv
        return functools.update_wrapper(cmd_proxy, func)
    return env_updater


def installer(func):
    """Decorate a click command as an ``installer``.

    Adds installer information to the click context object which
    is in turn passed to the decoratee command function.

    Wraps the command function in a function for result chaining.
    """
    @click.pass_context
    def cmd_proxy(ctx, *args, **kw):
        f_name = func.__name__
        tmpdir = tempfile.mkdtemp(suffix='-db-build-downloads')
        download_dir = os.path.join(tmpdir, f_name)
        install_dir = os.path.join(os.path.expanduser('~'), f_name)
        version = get_deploy_versions()[f_name]
        for path in (download_dir, install_dir):
            os.makedirs(path, exist_ok=True)
        meta = Meta(download_dir=download_dir,
                    install_dir=install_dir,
                    version=version)
        return ctx.invoke(func, meta, *args[1:], **kw)

    def command_proxy(*args, **kw):
        return functools.partial(cmd_proxy, *args, **kw)

    return functools.update_wrapper(command_proxy, func)


@click.group(chain=True, invoke_without_command=False)
@log_level_option(default='INFO')
@click.pass_context
def build(ctx, log_level):
    setup_logging(log_level=log_level)


@build.resultcallback()
def pipeline(installers, log_level):
    for installer in installers:
        installer()


@build.command()
@option('--ftp-host',
        default='ftp.ebi.ac.uk',
        help='FTP hostname for ACeDB data.')
@option('--remote-path-template',
        default='pub/databases/wormbase/releases/{version}/acedb',
        help='Path to the file(s) containing compressed database.')
@option('--file-selector-regexp',
        default='.*\.tar\.gz$',
        help='File selection regexp')
@persists_env()
@installer
def acedb_data(meta,
               ftp_host,
               remote_path_template,
               file_selector_regexp):
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
    os.environ['ACEDB_DATABASE'] = install_dir


@build.command()
@option('-t', '--url-template',
        default=('ftp://ftp.sanger.ac.uk/pub/acedb/MONTHLY/'
                 'ACEDB-binaryLINUX_{version}.tar.gz'),
        help='URL for versioned ACeDB binaries')
@installer
def acedb(meta, url_template):
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
    _make_executable(os.path.join(install_dir, 'tace'), logger)


@build.command()
@option('-t', '--url-template',
        default='https://my.datomic.com/downloads/free/{version}',
        help='URL template for Datomic Free version')
@persists_env()
@installer
def datomic_free(meta, url_template):
    install_dir = meta.install_dir
    version = meta.version
    url = url_template.format(version=version)
    fullname = 'datomic-free-{version}'.format(version=version)
    local_filename = fullname + '.zip'
    download_path = os.path.join(meta.download_dir, local_filename)
    logger.info('Downloading and extracting {} to {}', fullname, install_dir)
    with zipfile.ZipFile(download(url, download_path)) as zf:
        zf.extractall(install_dir)
    logger.info('Installed {} into {}', fullname, install_dir)
    datomic_home = os.path.join(install_dir, fullname)
    logger.info('Setting environment variable DATOMIC_HOME={}', datomic_home)
    os.environ['DATOMIC_HOME'] = datomic_home
    bin_dir = os.path.join(datomic_home, 'bin')
    for filename in os.listdir(bin_dir):
        bin_path = os.path.join(bin_dir, filename)
        _make_executable(bin_path, logger)
    os.chdir(datomic_home)
    mvn_install = os.path.join('bin', 'maven-install')
    logger.info('Installing datomic via {}', os.path.abspath(mvn_install))
    mvn_install_out = local(mvn_install)
    logger.info('Installed datomic_free')
    logger.debug(mvn_install_out)


@build.command()
@persists_env()
@installer
def pseudoace(meta):
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
    assert install_dir.startswith(os.path.expanduser('~'))
    shutil.rmtree(install_dir)
    shutil.move(src_path, install_dir)
    os.environ['PSEUDOACE_HOME'] = install_dir
    logger.info('Extracted pseudoace-{} to {}', tag, install_dir)


cli = build()
