import os

from configobj import ConfigObj
import click

from .import log
from . import notifications
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
    ctx.obj = util.CommandContext(base_path)
    log.setup_logging(os.path.join(os.path.expanduser('~logs')),
                      log_level=log_level)


@root_command.command()
@util.option('-c', '--slack-channel',
             default=notifications.DEFAULTS['channel'],
             help='Name of channel notifications will be sent to')
@click.argument('slack_url', type=notifications.SLACK_HOOK_URL)
def configure(slack_url, slack_channel):
    """Configure azanium.

    - Notifications to Slack
    """
    az_conf = ConfigObj()
    az_conf[notifications.__name__] = dict(notifications.DEFAULTS,
                                           url=slack_url,
                                           channel=slack_channel)
    with open(notifications.CONF_PATH, 'wb') as fp:
        az_conf.write(fp)
