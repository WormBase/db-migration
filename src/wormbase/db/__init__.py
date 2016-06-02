import logging

import click

from .util import CommandAssist
from .util import option


@click.group(chain=True, invoke_without_command=True)
@option('-l',
        '--log-filename',
        default=None,
        help='Logs to a specified filename (stdout/stderr by default.')
@option('--log-level',
        default='INFO',
        type=click.Choice(choices=('DEBUG', 'INFO', 'WARNING', 'ERROR')),
        help='Logging level.')
@click.pass_context
def build(ctx, log_filename, log_level):
    logging.basicConfig(filename=log_filename)
    ctx.obj = CommandAssist(__package__)
