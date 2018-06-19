import os

from configobj import ConfigObj
import click

from . import config
from . import log
from . import notifications
from . import util

DEFAULT_BASE_PATH = '/wormbase'

@util.command_group()
@util.log_level_option()
@util.option('-b', '--base-path',
             default=DEFAULT_BASE_PATH,
             type=click.types.Path(exists=True,
                                   file_okay=False,
                                   dir_okay=True,
                                   allow_dash=True,
                                   readable=True,
                                   writable=True),
             help=('The default base directory all software and data '
                   'will be installed into ({}).'.format(DEFAULT_BASE_PATH)))


@click.pass_context
def root_command(ctx, log_level, base_path):
    """WormBase DB Migration Command Line Tool."""
    os.makedirs(base_path, exist_ok=True)
    command_context = util.CommandContext(base_path)
    ctx.obj = command_context
    logfile_path = os.path.join(base_path,
                                'logs',
                                '{}.log'.format(__package__))
    command_context.logfile_path = logfile_path
    log.setup_logging(logfile_path, log_level=log_level)


@root_command.command()
@click.argument('ws_release_ftp_url')
@click.option('--slack-url',
              default=None,
              type=notifications.SLACK_HOOK_URL)
def configure(ws_release_ftp_url, slack_url=None):
    """Configure azanium.

    - Notifications to Slack
    """
    if os.path.isfile(config.PATH):
        az_conf = config.parse()
    else:
        az_conf = ConfigObj()
    az_conf['sources'] = dict(ws_release=ws_release_ftp_url)
    notifications_key = notifications.__name__
    if slack_url is not None:
        ncnf = az_conf.setdefault(notifications_key, notifications.DEFAULTS)
        ncnf.update(dict(slack_url=slack_url))
    if notifications_key not in az_conf:
        click.echo('Slack URL not provided, integration will be disabled')
        click.echo('No notifications will be sent for migration commands',
                   color='red')

    with open(config.PATH, 'wb') as fp:
        az_conf.write(fp)


@root_command.command()
@click.argument('message')
@util.pass_command_context
def notify(context, message):
    return notifications.notify(message)
