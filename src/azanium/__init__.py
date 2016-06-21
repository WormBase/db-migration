import os

from botocore.exceptions import ClientError
from configobj import ConfigObj
import click

from . import awsiam
from . import config
from . import log
from . import notifications
from . import params
from . import util

INSTANCE_BASE_PATH = '/media/ephemeral0/wormbase'

@util.command_group()
@util.log_level_option()
@util.option('-b', '--base-path',
             default=INSTANCE_BASE_PATH,
             type=params.PlatformAwareDirectory(),
             help=('The default base directory all software and data '
                   'will be installed into.'))
@util.option('--profile',
             default='default',
             help='AWS profile')
@util.option('--assume-role',
             default=awsiam.DB_MIG_ROLE,
             help='AWS Role that will be assumed.')
@click.pass_context
def root_command(ctx, log_level, base_path, profile, assume_role):
    """WormBase DB Migration Command Line Tool."""
    os.makedirs(base_path, exist_ok=True)
    command_context = util.CommandContext(base_path, profile, assume_role)
    session = awsiam.make_session(profile_name=command_context.profile)
    iam = session.resource('iam')
    role = iam.Role(command_context.assume_role)
    try:
        role.load()
    except ClientError as e:
        print(e)
        ctx.exit()
    (profile_name, ar_profile_name) = awsiam.ensure_config(command_context,
                                                           session,
                                                           role)
    if ar_profile_name is not None:
        profiles = session._session.full_config['profiles']
        ar_profile = profiles[ar_profile_name]
        try:
            session = awsiam.make_session(profile_name)
        except ClientError:
            pass
        else:
            ctx.assumed_role = ar_profile['role_arn']
    command_context.session = session
    command_context.assumed_profile = ar_profile_name
    command_context.user_profile = profile
    command_context.db_mig_state = util.aws_state()
    ctx.obj = command_context
    log.setup_logging(os.path.join(base_path, 'logs'), log_level=log_level)


@root_command.command()
@click.argument('slack_url', type=notifications.SLACK_HOOK_URL)
def configure(slack_url):
    """Configure azanium.

    - Notifications to Slack
    """
    az_conf = ConfigObj()
    az_conf[notifications.__name__] = dict(notifications.DEFAULTS,
                                           url=slack_url)
    with open(config.PATH, 'wb') as fp:
        az_conf.write(fp)
