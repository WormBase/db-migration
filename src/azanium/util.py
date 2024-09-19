# -*- coding: utf-8 -*-
import collections
import contextlib
import ftplib
import functools
import itertools
import logging
import operator
import os
import psutil
import re
import shelve
import subprocess
import stat
import tempfile
import time
import urllib.parse

from pkg_resources import resource_filename
import click
import configobj
import requests

from . import config
from . import notifications


def _secho(message, prefix='🐛  ', **kw):
    message = '{} {}'.format(prefix, message)
    return click.secho(message, **kw)


echo_info = functools.partial(_secho, fg='blue', bold=True)

echo_sig = functools.partial(click.secho, fg='green', bold=True)

echo_waiting = functools.partial(_secho, nl=False)

echo_retry = functools.partial(click.secho, fg='cyan')

pkgpath = functools.partial(resource_filename, __package__)


def app_state():
    return shelve.open(os.path.expanduser('~/.db-migration.db'))


def echo_warning(message,
                 prefix='⚠ WARNING!:',
                 fg='yellow',
                 bold=True,
                 notify=True):
    if notify:
        notifications.notify(message, icon_emoji=':warning', color='warning')
    return _secho(message, prefix=prefix, fg=fg, bold=bold)


def echo_error(message, err=True, fg='red', bold=True, notify=True):
    if notify:
        notifications.notify(message,
                             icon_emoji=':fire:',
                             color='warning')
    return _secho(message, err=err, fg=fg, bold=bold)


def echo_exc(message, err=True, fg='red', bold=True):
    return _secho(message, err=err, fg=fg, bold=bold)


class LocalCommandError(Exception):
    """Raised for commands that produce output on stderr."""


def markdown_table(rows):
    column_matrix = list(map(list, itertools.zip_longest(*rows)))
    len_matrix = map(list, (map(len, columns) for columns in column_matrix))
    col_max_lens = list(max(lens) for lens in len_matrix)
    divider = []
    matrix = collections.deque(rows)
    header_row = matrix.popleft()
    # 0th element: Class name
    # 1th element: datomic ident
    # rest are counts.
    rows = tuple(set(tuple(row[0:2]) + tuple(map(int, row[2:]))
                     for row in matrix))
    matrix = sorted(rows, key=operator.itemgetter(2), reverse=True)
    matrix.insert(0, header_row)
    matrix = list(map(str, row) for row in matrix)
    for i, columns in enumerate(column_matrix):
        divider.append('-' * col_max_lens[i])
    matrix.insert(1, divider)
    lines = []
    for row in matrix:
        line = ['| ']
        for j, cell in enumerate(row):
            line.append(' {} '.format(cell.rjust(col_max_lens[j])))
            line.append(' |')
        lines.append(''.join(line))
    return os.linesep.join(lines)


def split_ftp_url(ftp_url):
    """Parse an ``ftp_url`` and return three components: host, path and the
    WS_RELEASE version code.

    :param ftp_url: The FTP url
    :type ftp_url: str
    :returns: tuple of host, path and WS_RELEASE version code.
    :raises: ValueError if the FTP url is not valid. (must have ftp scheme)"""
    pr = urllib.parse.urlparse(ftp_url)
    if pr.scheme != 'ftp':
        raise ValueError('Unsupported URL type. Must be ftp://...')
    version = list(filter(None, pr.path.rsplit('/', 2)))[-1]
    return (pr.netloc, pr.path, version)


def local(cmd,
          input=None,
          timeout=None,
          shell=True,
          output_decoding='utf-8',
          cwd=None):
    """Run a command locally.

    :param cmd: The command to execute.
    :type cmd: str
    :param input: Optional text to pipe as input to `cmd`.
    :type input: str
    :param timeout: Optional number of seconds to wait for `cmd` to execute.
    :param timeout: int
    :param shell: Whether or not to execute `cmd` in a shell (Default: True)
    :type shell: boolean
    :param output_decoding: The encoding to decode the binary result of `cmd`.
                            Default: utf-8.
    :type output_decoding: str
    :returns: The result of the command
    :raises: LocalCommandError if result code was non-zero.
    """
    if isinstance(cmd, (list, tuple)) and shell:
        cmd = ' '.join(cmd)
    if input:
        input_stream = input.encode(output_decoding)
    else:
        input_stream = None
    proc = subprocess.Popen(cmd,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            cwd=cwd,
                            shell=shell)
    (out, err) = proc.communicate(input=input_stream, timeout=timeout)
    if proc.returncode != 0:
        raise LocalCommandError(err)
    return out.decode(output_decoding)


def setup_py(rest_of_args):
    return local('python setup.py ' + rest_of_args).strip()


def distribution_name():
    return setup_py(' --fullname')


def option(*args, **kw):
    """Factory function for click.option that makes help text more useful.

    When emitted, the help text will display any default passed to the option.

    :returns: Same object as `click.option`.
    """
    default = kw.get('default')
    if default is not None:
        s_default = str(default)
    else:
        s_default = ''
    help_text = kw.get('help', '')
    if all((s_default, help_text, s_default not in help_text)):
        kw['help'] = help_text + ' Default: ' + s_default
    return click.option(*args, **kw)


log_level_option = functools.partial(
    option,
    '-l',
    '--log-level',
    default='INFO',
    type=click.Choice(choices=('DEBUG', 'INFO', 'WARNING', 'ERROR')),
    help='Logging level.')


def download(url, local_filename, chunk_size=1024 * 10):
    """Download `url` into `local_filename'.

    :param url: The URL to download from.
    :type url: str
    :param local_filename: The local filename to save into.
    :type local_filename: str
    :param chunk_size: The size to download chunks in bytes (10Kb by default).
    :type chunk_size: int
    :rtype: str
    :returns: The path saved to.
    """
    response = requests.get(url)
    with open(local_filename, 'wb') as fp:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                fp.write(chunk)
    return fp.name


@contextlib.contextmanager
def ftp_connection(host, logger):
    logger.info('Connecting to {}', host)
    ftp = ftplib.FTP(host=host, user='anonymous')
    ftp.set_pasv(True)
    yield ftp
    logger.info('Disconnecting from {}', host)
    ftp.quit()


def ftp_download(host,
                 file_selector_regexp,
                 download_dir,
                 logger=None,
                 initial_cwd=None):
    if logger is None:
        logger = logging.getLogger(__package__)
    downloaded = []
    file_selector = functools.partial(re.match, file_selector_regexp)
    with ftp_connection(host, logger) as ftp:
        if initial_cwd is not None:
            ftp.cwd(initial_cwd)
        filenames = filter(file_selector, ftp.nlst('.'))
        for filename in filenames:
            out_path = os.path.join(download_dir, filename)
            logger.info('Saving {} to {}', filename, out_path)
            with open(out_path, 'wb') as fp:
                ftp.retrbinary('RETR ' + filename, fp.write)
            downloaded.append(fp.name)
    return downloaded


def get_ftp_url():
    return config.parse().get('sources', {}).get('ws_release_ftp')


def get_data_release_version():
    return config.parse().get('sources', {}).get('ws_release_name')

def parse_data_release_version(release_tag=None):
    release_name = None
    if release_tag is None:
        release_tag = ws_release_tag()
    if not release_tag:
        raise ValueError('Release tag has not been configured.')

    regex = re.compile(r'models\.wrm\.(.+)')
    match = regex.fullmatch(release_tag)
    if match:
        release_name = match.group(1)
    else:
        raise ValueError('Release tag does not comply to regex r\''+regex.pattern+'\'.')

    return release_name

def ws_release_tag():
    return config.parse().get('sources', {}).get('ws_release_tag')

def get_deploy_versions(purpose='default'):
    path = resource_filename(__package__, 'cloud-config/versions.ini')
    with open(path) as fp:
        co = configobj.ConfigObj(infile=fp)
    dv = dict(co)[purpose]
    dv['acedb_database'] = dv['acedb_id_catalog'] = get_data_release_version()
    return dv


def jvm_mem_opts(pct_of_free_mem):
    bytes_free = psutil.virtual_memory().free
    gb_free = bytes_free // (2 ** 30)
    max_heap_size = round(gb_free * pct_of_free_mem)
    init_heap_size = max_heap_size
    format_Gb = '{:d}G'.format
    return ' '.join(['-Xmx' + format_Gb(max_heap_size),
                     '-Xms' + format_Gb(init_heap_size)])


def make_executable(path, logger, mode=0o775, symlink_dir='~/.local/bin'):
    logger.info('Setting permissions on {} to {}',
                path,
                stat.filemode(mode))
    os.chmod(path, mode)
    if symlink_dir is not None:
        bin_dirname = os.path.abspath(os.path.expanduser(symlink_dir))
        bin_filename = os.path.basename(path)
        bin_path = os.path.join(bin_dirname, bin_filename)
        if os.path.islink(bin_path):
            os.unlink(bin_path)
        os.symlink(path, bin_path)
        logger.debug('Created symlink from {} to {}', path, bin_path)


class CommandContext:

    def __init__(self, base_path):
        self.base_path = base_path
        self.logfile_path = ''

    @property
    def java_cmd(self):
        return 'java -server ' + jvm_mem_opts(0.75)

    @property
    def pseudoace_jar_path(self):
        versions = get_deploy_versions()
        jar_name = 'pseudoace-{[pseudoace]}.jar'.format(versions)
        return os.path.join(self.path('pseudoace'), jar_name)

    @property
    def db_name(self):
        return get_data_release_version()

    @property
    def app_state(self):
        state = getattr(self, '_app_state', None)
        if state is None:
            state = self._app_state = app_state()
        return state

    @property
    def qa_report_path(self):
        return self.path('{}-report.csv'.format(get_data_release_version()))

    def path(self, *args):
        return os.path.join(self.base_path, *args)

    def exists(self, path):
        return os.path.exists(path)

    def datomic_url(self,
                    db_name=None,
                    default_prefix='datomic:free://localhost:4334/'):
        if db_name is None:
            db_name = self.db_name
        default_url = default_prefix + db_name
        return os.environ.get('DATOMIC_URI', default_url)


pass_command_context = click.make_pass_decorator(CommandContext)

command_group = functools.partial(click.group, context_settings={
    'help_option_names': ['-h', '--help']
})


def touch_dir(path):
    """Updates access + modified times for a directory.

    Done by writing and immediately removing a temporary file within `dirpath`.

    :param path: Path to a directory.
    :type: str
    """
    assert os.path.isdir(path)
    with tempfile.NamedTemporaryFile(dir=path, suffix='azanium', mode='wb'):
        pass


def retries(attempts, callback):
    while attempts > 0:
        try:
            callback()
        except LocalCommandError:
            attempts -= 1
            click.echo("Retrying %d more times..." % attempts)
        time.sleep(0.5)
    return attempts > 0

