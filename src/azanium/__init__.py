import click

from .import log
from . import util


@util.command_group()
@util.log_level_option()
@click.pass_context
def root_command(ctx, log_level):
    """A WormBase DB Migration Command Line Tool."""
    log.setup_logging(log_level=log_level)
