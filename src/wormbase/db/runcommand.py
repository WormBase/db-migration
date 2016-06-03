import logging
import os

import click

from .util import CommandAssist
from .util import pass_command_assist
from .util import get_deploy_versions
from .util import local
from .util import log_level_option
from .util import log_filename_option
from .util import option


@click.group()
@log_filename_option()
@log_level_option()
@click.pass_context
def run(ctx, log_filename, log_level):
    logging.basicConfig(filename=log_filename)
    ctx.obj = CommandAssist(__name__, log_level=log_level)


@run.command()
@option('-d',
        '--acedb-dump-dir',
        help='ACeDB dump directory (ace files)')
@option('-c',
        '--tace-dump-options',
        default='-s -T -C',
        help='tace "Dump" command options')
@pass_meta
def acedb_dump(assister, acedb_dump_dir, tace_dump_options):
    acedb_data_dir = os.environ['ACEDB_DATABASE']
    data_release = get_deploy_versions()['acedb_data']
    acedb_dump_dir = os.path.join(os.path.expanduser('~/acedb'),
                                  'dump',
                                  data_release)
    tace_dump_cmd = 'Dump {} {}'.format(tace_dump_options, acedb_dump_dir)
    with run_local_command(['tace', acedb_data_dir],
                           stdin=tace_dump_cmd) as proc:
        if proc.returnvalue != 0:
            assister.log_error(proc.stderr.read())
