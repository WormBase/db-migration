import os

import click

from . import build
from .install import pass_meta
from .util import CommandLogger
from .util import get_deploy_versions
from .util import option
from .util import run_local_command


@build.group()
@click.pass_context
def run(ctx, log_filename, log_level):
    ctx.obj = CommandLogger(log_level=log_level)


@run.resultcallback()
def pipeline(steps):
    for step in steps:
        step()


@run.command
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
