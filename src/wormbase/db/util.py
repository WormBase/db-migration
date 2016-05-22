# -*- coding: utf-8 -*-
import functools

import click
import requests


def option(*args, **kw):
    """Factory function for click.option that makes help text more useful.

    When emitted, the help text will display any default passed to the option.

    :returns: Same object as `click.option`.
    """
    default = kw.get('default')
    if default is not None:
        s_default = str(default)
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


echo_info = functools.partial(_secho, fg='blue', bold=True)

echo_sig = functools.partial(click.secho, fg='green', bold=True)

echo_waiting = functools.partial(_secho, nl=False)

echo_retry = functools.partial(click.secho, fg='cyan')

echo_error = functools.partial(_secho,
                               err=True,
                               fg='yellow',
                               bg='red',
                               bold=True)
