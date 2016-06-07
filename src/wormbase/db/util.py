# -*- coding: utf-8 -*-
import functools
import gzip
import itertools
import os
import subprocess

from pkg_resources import resource_filename
import click
import configobj
import requests


def _secho(message, **kw):
    message = '🐛 -> {}'.format(message)
    return click.secho(message, **kw)


echo_info = functools.partial(_secho, fg='blue', bold=True)

echo_sig = functools.partial(click.secho, fg='green', bold=True)

echo_waiting = functools.partial(_secho, nl=False)

echo_retry = functools.partial(click.secho, fg='cyan')

echo_error = functools.partial(_secho,
                               err=True,
                               fg='yellow',
                               bg='red',
                               bold=True)

pkgpath = functools.partial(resource_filename, __package__)

install_path = functools.partial(os.path.join, '/datastore', 'wormbase')


class LocalCommandError(Exception):
    """Raised for commands that produce output on stderr."""


def local(cmd, input=None, timeout=None, shell=True, output_decoding='utf-8'):
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
                            shell=shell,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    (out, err) = proc.communicate(input=input_stream, timeout=timeout)
    if proc.returncode != 0:
        raise LocalCommandError(err)
    return out.decode(output_decoding)


def distribution_name():
    return local('python setup.py --fullname').rstrip()


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
    '--log-level',
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


def get_deploy_versions(purpose='default'):
    path = resource_filename(__package__, 'cloud-config/versions.ini')
    with open(path) as fp:
        co = configobj.ConfigObj(infile=fp)
    return dict(co)[purpose]


def partition(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    for seq in itertools.zip_longest(*args, fillvalue=fillvalue):
        yield filter(os.path.isfile, seq)


def sort_edn_log(path):
    out_path = path.replace('.gz', '.sort.gz')
    try:
        with gzip.open(path) as fp:
            lines = fp.readlines()
        lines.sort()
        with gzip.open(out_path, 'wb') as fp:
            fp.write(gzip.compress(b''.join(lines)))
        return True
    finally:
        if os.path.isfile(out_path):
            os.remove(path)
    return False
