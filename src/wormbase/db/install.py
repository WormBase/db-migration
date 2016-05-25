import atexit
import collections
import contextlib
import ftplib
import functools
import getpass
import hashlib
import io
import logging
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.parse
import zipfile

import click

from .util import download
from .util import echo_info
from .util import echo_sig
from .util import echo_waiting
from .util import option
from .util import get_deploy_versions

from . import github

logger = logging.getLogger(__name__)

Meta = collections.namedtuple('Meta', ('download_dir',
                                       'install_dir',
                                       'version'))

_temp_dirs = []


def _mk_temp_dir(purpose):
    tempdir = tempfile.mkdtemp(suffix=purpose)
    global _temp_dirs
    _temp_dirs.append(tempdir)
    return tempdir


def _append_line(text, filename, backup=True):
    path = os.path.expanduser(filename)
    with open(path) as fp:
        lines = list(fp)
    if text not in set(map(str.rstrip, lines)):
        lines.append(text)
        lines.append(os.linesep)
    if backup:
        os.rename(path, path + '.{}.bakup'.format(time.time()))
    with open(path, 'w') as fp:
        for line in lines:
            fp.write(line)


def _acedb_data_checksums(ftp, release):
    chksums = {}
    buf = io.BytesIO()
    ftp.retrbinary('RETR md5sum.{}'.format(release), buf.write)
    for line in buf.getvalue().splitlines():
        (chksum, path) = line.split()
        path = os.path.basename(path).decode('ascii')
        chksums[path] = chksum.decode('ascii')
    return chksums


@atexit.register
def _clean_temp_dirs():
    for path in _temp_dirs:
        shutil.rmtree(path)


@contextlib.contextmanager
def _ftp(host):
    ftp = ftplib.FTP(host=host, user='anonymous')
    ftp.set_pasv(True)
    yield ftp
    ftp.quit()


def persists_path(shell_init_file='~/.bashrc'):
    """Decorator for a `install` command.

    The decorated function should return a path to be appended
    to the current users ${PATH} specified in the user's shell profile.
    """
    def path_updater(func):
        def cmd_proxy(*args, **kw):
            install_path = func(*args, **kw)
            new_line = 'export PATH="${PATH}:%s' % install_path
            _append_line(new_line, filename=shell_init_file)
            msg = 'Added {text!r} to $PATH for {user}'
            msg = msg.format(text=new_line, user=getpass.getuser())
            echo_info(msg)
            return install_path
        return functools.update_wrapper(cmd_proxy, func)
    return path_updater


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
            env_vars = dict(env_before - env_after)
            for (env_var, val) in sorted(env_vars.items()):
                new_line = 'export {var}="{val}"'.format(var=env_var, val=val)
                _append_line(new_line, filename=shell_init_file)
            msg = 'Updated environemnt for {user}'
            msg = msg.format(msg, user=getpass.getuser())
            echo_info(msg)
            return rv
        return functools.update_wrapper(cmd_proxy, func)
    return env_updater


def pass_meta(func):
    """Decorator for automating specification of meta-data to sub-commands.
    """
    @click.pass_context
    def command_with_meta_info(ctx, *args, **kw):
        f_name = func.__name__
        tmpdir = _mk_temp_dir('-db-build-downloads')
        download_dir = os.path.join(tmpdir, f_name)
        install_dir = os.path.join(os.path.expanduser('~'), f_name)
        version = get_deploy_versions()[f_name]
        for path in (download_dir, install_dir):
            if not os.path.isdir(path):
                os.makedirs(path)
        ctx.obj = Meta(download_dir=download_dir,
                       install_dir=install_dir,
                       version=version)
        obj = ctx.find_object(Meta)
        return ctx.invoke(func, obj, *args[1:], **kw)
    return functools.update_wrapper(command_with_meta_info, func)


@click.group()
@click.pass_context
def install(ctx):
    pass


@install.command()
@option('--ftp-host',
        default='ftp.ebi.ac.uk',
        help='FTP hostname for ACeDB data.')
@option('--remote-path-template',
        default='pub/databases/wormbase/releases/{version}/acedb',
        help='Path to the file(s) containing compressed database.')
@option('--file-selector-regexp',
        default='.*\.tar\.gz$',
        help='File selection regexp')
@pass_meta
@installer
@persists_env()
def acedb_data(meta,
               ftp_host,
               remote_path_template,
               file_selector_regexp):
    download_dir = meta.install_dir
    os.chdir(download_dir)
    format_path = remote_path_template.format
    md5sum = lambda data: hashlib.new('md5', data).hexdigest()
    file_selector = functools.partial(re.match, file_selector_regexp)
    version = meta.version
    with _ftp(ftp_host) as ftp:
        ftp.cwd(format_path(version=version))
        chksums = _acedb_data_checksums(ftp, version)
        filenames = filter(file_selector, ftp.nlst('.'))
        for filename in filenames:
            out_path = os.path.join(download_dir, filename)
            try:
                with open(out_path, 'rb') as fp:
                    chksum = chksums.get(filename, '')
                    if chksum == md5sum(fp.read()):
                        click.echo('')
                        msg = 'Skipping existing file: {} (md5:{})'
                        logger.info(msg.format(filename, chksum))
                        continue
            except IOError:
                pass
            msg = 'Saving {} to {} ... '.format(filename, out_path)
            logger.info(msg)
            echo_waiting(msg)
            with open(filename, 'wb') as fp:
                ftp.retrbinary('RETR ' + filename, fp.write)
            os.chmod(os.path.join(download_dir, 'INSTALL'), 0o775)
            echo_sig('done')
    # Enable the Dump command
    passwd_path = os.path.join(meta.install_dir, 'wspec', 'passwd.wrm')
    os.chmod(passwd_path, 0o644)
    with open(passwd_path, 'a') as fp:
        fp.write(getpass.getuser() + os.linesep)
    subprocess.check_call('./INSTALL', cwd=meta.install_dir, shell=True)
    os.environ['ACEDB_DATABASE'] = meta.install_dir


@install.command()
@option('-t', '--url-template',
        default=('ftp://ftp.sanger.ac.uk/pub/acedb/MONTHLY/'
                 'ACEDB-binaryLINUX_{version}.tar.gz'),
        help='URL for 64bit version of ACeDB binaries')
@persists_path()
@pass_meta
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
            echo_waiting('Downloading {} ... '.format(filename))
            ftp.retrbinary('RETR ' + filename, fp.write)
            echo_sig('done')
    with tarfile.open(local_filename) as tf:
        tf.extract('./tace', path=install_dir)
    return install_dir


@install.command()
@option('-t', '--url-template',
        default='https://my.datomic.com/downloads/free/{version}',
        help='URL template for Datomic Free version')
@persists_env()
@persists_path()
@pass_meta
def datomic_free(meta, url_template):
    version = meta.version
    url = url_template.format(version=version)
    fullname = 'datomic-free_{version}'.format(version=version)
    local_filename = fullname + '.zip'
    download_path = os.path.join(meta.download_dir, local_filename)
    with zipfile.ZipFile(download(url, download_path)) as zf:
        zf.extractall(meta.install_dir)
    datomic_home = os.path.join(meta.install_dir, fullname)
    os.environ['DATOMIC_HOME'] = datomic_home
    return os.path.join(datomic_home, 'bin')


@install.command()
@pass_meta
def pseudoace(meta):
    download_dir = meta.download_dir
    install_dir = meta.install_dir
    tag = meta.version
    echo_waiting('Downloading pseudoace from github ... ')
    dl_path = github.download_release_binary(
        'WormBase/pseudoace',
        tag,
        to_directory=download_dir)
    echo_sig('done')
    tempdir = tempfile.mkdtemp()
    with tarfile.open(dl_path) as tf:
        tf.extractall(path=tempdir)
    fullname = 'pseudoace-' + tag
    tmp_src_path = os.path.join(tempdir, fullname)
    src_path = tmp_src_path.rstrip('-' + tag)
    os.rename(tmp_src_path, src_path)
    os.rmdir(install_dir)
    shutil.move(src_path, install_dir)


cli = install(obj={})
