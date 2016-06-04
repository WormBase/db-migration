import logging
import os

import click

from .util import option


@click.group(chain=True, invoke_without_command=True)
@option('-l',
        '--log-level',
        default='INFO',
        help='Logging level')
@click.pass_context
def build(ctx, log_level):
    log_filename = os.path.expanduser('~/wb-build-db.log')
    logging.basicConfig(filename=log_filename, level=log_level)
