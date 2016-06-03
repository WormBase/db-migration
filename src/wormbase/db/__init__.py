import logging

import click

from .util import CommandAssist


@click.group(chain=True, invoke_without_command=True)
@click.pass_context
def build(ctx, log_filename, log_level):
    logging.basicConfig(filename=log_filename)
    ctx.obj = CommandAssist(__package__)
