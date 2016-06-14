import os

import click

from .import log
from . import util


@util.command_group()
@util.log_level_option()
@util.option('-b', '--base-path',
             default='/media/ephemeral0/wormbase',
             help=('The default base directory all software and data '
                   'will be installed into'))
@click.pass_context
def root_command(ctx, log_level, base_path):
    """A WormBase DB Migration Command Line Tool."""
    ctx.obj = util.EC2InstanceCommandContext(base_path=base_path)
    log.setup_logging(os.path.join(base_path, 'logs'),
                      log_level=log_level)
