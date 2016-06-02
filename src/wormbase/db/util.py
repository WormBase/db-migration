# -*- coding: utf-8 -*-
import functools
import logging
import subprocess

from pkg_resources import resource_filename
import click
import configobj
import requests


class CommandAssist:

    def __init__(self, namespace, log_level=logging.INFO):
        self._log_level = log_level
        self._logger_name = namespace
        self._logger = logging.getLogger(self._logger_name)
        self._logger.setLevel(log_level)
        self.meta = {}

    def __getattr__(self, name):
        if not name.startswith('_'):
            return getattr(self._logger, name)
        raise AttributeError(name)


pass_command_assist = click.make_pass_decorator(CommandAssist)


class LocalCommandError(Exception):
    """Raised for commands that produce output on stderr."""


def run_local_command(cmd, stdin=None, timeout=None, shell=True):
    if isinstance(cmd, (list, tuple)) and shell:
        cmd = ' '.join(cmd)
    proc = subprocess.Popen(cmd,
                            shell=shell,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    (out, err) = proc.communicate(input=stdin, timeout=timeout)
    if err:
        raise LocalCommandError(err)
    return out.decode('utf-8')


def distribution_name():
    return run_local_command('python setup.py --fullname').rstrip()


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
    help_text = kw.get('help')
    if all((s_default, help_text, s_default not in help_text)):
        kw['help'] = help_text + ' Default: ' + s_default
    return click.option(*args, **kw)


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


def _secho(message, **kw):
    message = '🐛 -> {}'.format(message)
    return click.secho(message, **kw)


def get_deploy_versions(purpose='default'):
    path = resource_filename(__package__, 'cloud-config/versions.ini')
    with open(path) as fp:
        co = configobj.ConfigObj(infile=fp)
    return dict(co)[purpose]


echo_info = functools.partial(_secho, fg='blue', bold=True)

echo_sig = functools.partial(click.secho, fg='green', bold=True)

echo_waiting = functools.partial(_secho, nl=False)

echo_retry = functools.partial(click.secho, fg='cyan')

echo_error = functools.partial(_secho,
                               err=True,
                               fg='yellow',
                               bg='red',
                               bold=True)
