import collections
import functools
import os
import tempfile

import click

from . import util

Info = collections.namedtuple('Info', ('download_dir',
                                       'install_dir',
                                       'version'))
DOWNLOAD_DIR = '/tmp/downloads'

def prepare(cmd_ctx, func):
    f_name = func.__name__
    tmpdir = tempfile.mkdtemp(suffix='-db-migration-downloads',
                              dir=DOWNLOAD_DIR)
    download_dir = os.path.join(tmpdir, f_name)
    install_dir = cmd_ctx.path(f_name)
    version = util.get_deploy_versions()[f_name]
    for path in (download_dir, install_dir):
        os.makedirs(path, exist_ok=True)
    return Info(download_dir=download_dir,
                install_dir=install_dir,
                version=version)


def prepared(func):
    """Decorator providing a click command function with download/install info.

    Fowards to the original function with addtional ``Info`` object
    containing details such as install and download disk locations.
    """
    @util.pass_command_context
    def cmd_proxy(cmd_ctx, *args, **kw):
        ctx = click.get_current_context()
        afct = prepare(cmd_ctx, func)
        return ctx.invoke(func, cmd_ctx, afct, *args[1:], **kw)

    # def command_proxy(*args, **kw):
    #     return functools.partial(cmd_proxy, *args, **kw)
    return functools.update_wrapper(cmd_proxy, func)
