import atexit
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

from . import build
from . import github
from .util import CommandAssist
from .util import download
from .util import get_deploy_versions
from .util import option
from .util import pass_command_assist
from .util import run_local_command

Meta = collections.namedtuple('Meta', ('download_dir',
                                       'install_dir',
                                       'version'))

_temp_dirs = []


def _mk_temp_dir(purpose):
    tempdir = tempfile.mkdtemp(suffix=purpose)
    global _temp_dirs
    _temp_dirs.append(tempdir)
    return tempdir


def _make_executable(path, assister, mode=0o775):
    assister.info('Setting permissions on %s to %s',
                path,
                stat.filemode(mode))
    os.chmod(path, mode)
    bin_dirname = os.path.expanduser('~/.local/bin')
    bin_filename = os.path.basename(path)
    bin_path = os.path.join(bin_dirname, bin_filename)
    if os.path.islink(bin_path):
        os.unlink(bin_path)
    os.symlink(path, bin_path)
    assister.info('Created symlink from %s to %s', path, bin_path)


# Uncomment to have download directories purge after installation.
# @atexit.register
def _clean_temp_dirs():
    for path in _temp_dirs:
        shutil.rmtree(path)


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
        tmpdir = _mk_temp_dir('-db-build-downloads')
        download_dir = os.path.join(tmpdir, f_name)
        install_dir = os.path.join(os.path.expanduser('~'), f_name)
        version = get_deploy_versions()[f_name]
        for path in (download_dir, install_dir):
            if not os.path.isdir(path):
                os.makedirs(path)
        obj = ctx.find_object(CommandAssist)
        obj.meta.update(Meta(download_dir=download_dir,
                             install_dir=install_dir,
                             version=version)._asdict())
        return ctx.invoke(func, obj, *args[1:], **kw)

    def command_proxy(*args, **kw):
        return functools.partial(cmd_proxy, *args, **kw)

    return functools.update_wrapper(command_proxy, func)


@build.resultcallback()
def pipeline(installers, log_filename, log_level):
    for installer in installers:
        installer()


@build.command('acedb-data')
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
@pass_command_assist
@installer
def acedb_data(assister,
               ftp_host,
               remote_path_template,
               file_selector_regexp):
    meta = assister.meta
    download_dir = meta['download_dir']
    install_dir = meta['install_dir']
    format_path = remote_path_template.format
    file_selector = functools.partial(re.match, file_selector_regexp)
    version = meta['version']
    assister.info('Connecting to %s', ftp_host)
    with _ftp(ftp_host) as ftp:
        ftp.cwd(format_path(version=version))
        filenames = filter(file_selector, ftp.nlst('.'))
        for filename in filenames:
            out_path = os.path.join(download_dir, filename)
            msg = 'Saving {} to {}'.format(filename, out_path)
            assister.info(msg)
            with open(out_path, 'wb') as fp:
                ftp.retrbinary('RETR ' + filename, fp.write)
            with tarfile.open(fp.name) as tf:
                assister.info('Extracting %s to %s', fp.name, install_dir)
                tf.extractall(path=install_dir)
    # Enable the Dump command
    passwd_path = os.path.join(install_dir, 'wspec', 'passwd.wrm')
    mode = 0o644
    assister.info('Changing permissions of %s to %s',
                  passwd_path,
                  stat.filemode(mode))
    os.chmod(passwd_path, mode)
    username = getpass.getuser()
    with open(passwd_path, 'a') as fp:
        assister.info('Adding %s to %s', username, passwd_path)
        fp.write(username + os.linesep)
    os.environ['ACEDB_DATABASE'] = install_dir


@build.command()
@option('-t', '--url-template',
        default=('ftp://ftp.sanger.ac.uk/pub/acedb/MONTHLY/'
                 'ACEDB-binaryLINUX_{version}.tar.gz'),
        help='URL for versioned ACeDB binaries')
@pass_command_assist
@installer
def acedb(assister, url_template):
    meta = assister.meta
    install_dir = meta['install_dir']
    download_dir = meta['download_dir']
    version = meta['version']
    url = url_template.format(version=version)
    pr = urllib.parse.urlparse(url)
    with _ftp(pr.netloc) as ftp:
        ftp.cwd(os.path.dirname(pr.path))
        filename = os.path.basename(pr.path)
        local_filename = os.path.join(download_dir, os.path.basename(pr.path))
        with open(local_filename, 'wb') as fp:
            assister.info('Downloading {}'.format(filename))
            ftp.retrbinary('RETR ' + filename, fp.write)
    with tarfile.open(local_filename) as tf:
        tf.extract('./tace', path=install_dir)
    _make_executable(os.path.join(install_dir, 'tace'), assister)


@build.command('datomic-free')
@option('-t', '--url-template',
        default='https://my.datomic.com/downloads/free/{version}',
        help='URL template for Datomic Free version')
@persists_env()
@pass_command_assist
@installer
def datomic_free(assister, url_template):
    meta = assister.meta
    install_dir = meta['install_dir']
    version = meta['version']
    url = url_template.format(version=version)
    fullname = 'datomic-free-{version}'.format(version=version)
    local_filename = fullname + '.zip'
    download_path = os.path.join(meta['download_dir'], local_filename)
    with zipfile.ZipFile(download(url, download_path)) as zf:
        zf.extractall(install_dir)
    assister.info('Installed %s into %s', fullname, meta['install_dir'])
    datomic_home = os.path.join(install_dir, fullname)
    os.environ['DATOMIC_HOME'] = datomic_home
    bin_dir = os.path.join(datomic_home, 'bin')
    for filename in os.listdir(bin_dir):
        bin_path = os.path.join(bin_dir, filename)
        _make_executable(bin_path, assister)
    os.chdir(datomic_home)
    mvn_install_out = run_local_command(['bin/maven-install'])
    assister.info('Installed datomic_free via maven')
    assister.debug(mvn_install_out)


@build.command()
@persists_env()
@pass_command_assist
@installer
def pseudoace(assister):
    meta = assister.meta
    download_dir = meta['download_dir']
    install_dir = meta['install_dir']
    tag = meta['version']
    assister.info('Downloading pseudoace release %s from github', tag)
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
    os.rmdir(install_dir)
    shutil.move(src_path, install_dir)
    os.environ['PSEUDOACE_HOME'] = install_dir
    assister.info('Extracted pseudoace-%s to %s', tag, install_dir)


cli = build()
