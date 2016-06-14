# -*- coding: utf-8 -*-
import functools
import os
import psutil
import shelve
import subprocess

from pkg_resources import resource_filename
import click
import configobj
import requests


def _secho(message, prefix='🐛  ', **kw):
    message = '{} {}'.format(prefix, message)
    return click.secho(message, **kw)


echo_info = functools.partial(_secho, fg='blue', bold=True)

echo_sig = functools.partial(click.secho, fg='green', bold=True)

echo_waiting = functools.partial(_secho, nl=False)

echo_warning = functools.partial(_secho,
                                 prefix='⚠ WARNING!:', fg='yellow', bold=True)

echo_retry = functools.partial(click.secho, fg='cyan')

echo_error = functools.partial(_secho,
                               err=True,
                               fg='red',
                               bold=True)

pkgpath = functools.partial(resource_filename, __package__)

install_path = functools.partial(os.path.join, '/media/ephemeral0/wormbase')

aws_state = functools.partial(shelve.open,
                              os.path.join(os.getcwd(), '.db-migration.db'))


class LocalCommandError(Exception):
    """Raised for commands that produce output on stderr."""


def local(cmd,
          input=None,
          timeout=None,
          shell=True,
          output_decoding='utf-8',
          cwd=None):
    """Run a command locally
.
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


def get_deploy_versions(purpose='default'):
    path = resource_filename(__package__, 'cloud-config/versions.ini')
    with open(path) as fp:
        co = configobj.ConfigObj(infile=fp)
    return dict(co)[purpose]


def jvm_mem_opts(pct_of_free_mem):
    bytes_free = psutil.virtual_memory().free
    gb_free = bytes_free // (2 ** 30)
    max_heap_size = round(gb_free * pct_of_free_mem)
    init_heap_size = max_heap_size
    format_Gb = '{:d}G'.format
    return ('-Xmx', format_Gb(max_heap_size),
            '-Xms', format_Gb(init_heap_size))


class EC2InstanceCommandContext:

    def __init__(self, *kw):
        self.__dict__.update(kw)
        self.versions = get_deploy_versions()

    @property
    def java_cmd(self):
        return 'java -server ' + ' '.join(jvm_mem_opts(0.75))

    @property
    def pseudoace_jar_path(self):
        jar_name = 'pseudoace-{[pseudoace]}.jar'.format(self.versions)
        return os.path.join(self.path('pseudoace'), jar_name)

    @property
    def data_release_version(self):
        return self.versions['acedb_database']

    path = staticmethod(install_path)

    def datomic_url(self,
                    db='',
                    protocol='free',
                    host='localhost',
                    port='4334'):
        db_name = db if db else self.data_release_version
        url = 'datomic:{protocol}://{host}:{port}/{db}'
        return url.format(protocol=protocol, host=host, port=port, db=db_name)


pass_ec2_command_context = click.make_pass_decorator(EC2InstanceCommandContext)

command_group = functools.partial(click.group, context_settings={
    'help_option_names': ['-h', '--help']
})
