import click

from . import install
from . import notifications
from . import root_command
from . import runcommand


cli = click.CommandCollection(sources=[
    install,
    notifications,
    runcommand
])

cli = root_command(obj={})
