import click

from . import admin
from . import awscloudops
from . import install
from . import notifications
from . import root_command
from . import runcommand


cli = click.CommandCollection(sources=[
    admin,
    awscloudops,
    install,
    notifications,
    runcommand
])

cli = root_command(obj={})
