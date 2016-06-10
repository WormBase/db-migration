import collections
import json

import click
from botocore.exceptions import ClientError

from . import awsiam
from . import log
from . import util


logger = log.get_logger(__name__)


AWSMeta = collections.namedtuple('AWSMeta', (
    'assume_role_policy_name',
    'group_name',
    'group_policies',
    'role_name',
    'role_policies'
))


_marker = object()


class AdminSession:

    def __init__(self, profile_name, **aws_meta):
        self.session = awsiam.make_session(profile_name)
        self.aws_state = util.aws_state()
        self.aws_meta = AWSMeta(**aws_meta)

    def __getattr__(self, name):
        for delegate in (self.session, self.aws_meta):
            value = getattr(delegate, name, _marker)
            if value is not _marker:
                return value
        raise AttributeError(name)


pass_admin_session = click.make_pass_decorator(AdminSession)


@click.group()
@util.option('--profile', default='default', help='aws profile name')
@util.log_level_option()
@click.option('-p',
              '--assume-role-policy-name',
              default=awsiam.DB_MIG_ROLE + '-assume',
              help='The name of the role to perform migration operations.')
@util.option('-g', '--group-name',
             default=awsiam.DB_MIG_GROUP,
             help='DB Migration user group name')
@util.option('-G', '--group-policies',
             default=awsiam.DB_MIG_GROUP_POLICIES,
             type=list,
             help='IAM Policies for the db migration group')
@util.option('-r', '--role-name',
             default=awsiam.DB_MIG_ROLE,
             help='aws role to be assumed')
@util.option('-R', '--role-policies',
             default=awsiam.DB_MIG_ROLE_POLICIES,
             help='Policies to be attached to the assume role')
@click.pass_context
def admin(ctx, profile, log_level, **aws_meta):
    log.setup_logging(log_level=log_level)
    ctx.obj = AdminSession(profile, **aws_meta)


@admin.command('setup',
               short_help='Configures all required IAM resources')
@pass_admin_session
def setup(session):
    iam = session.resource('iam')
    aws_meta = session.aws_meta
    ctx = click.get_current_context()
    try:
        group = awsiam.ensure_group(iam,
                                    group_name=aws_meta.group_name,
                                    group_policies=aws_meta.group_policies)
        role = awsiam.ensure_role(
            iam,
            role_name=aws_meta.role_name,
            role_policies=aws_meta.role_policies,
            group_name=aws_meta.group_name)
        awsiam.ensure_assume_role_policy(iam,
                                         role,
                                         aws_meta.assume_role_policy_name)
        ctx.invoke(sync_users, session)
    except Exception as e:
        util.echo_error(e)
        ctx.abort()
    else:
        click.secho('All required IAM resources configured', underline=True)
        click.secho('Role: ' + role.arn)
        click.secho('Group: ' + group.arn)
        arpn = aws_meta.assume_role_policy_name
        (user_data, errors) = awsiam.users(iam, arpn,
                                           role_name=role.name,
                                           group_name=group.name)
        assert not errors, 'Never-never land. This is a bug.'
        users = user_data['group']['users']
        click.secho('Users: ' + ', '.join(user['name'] for user in users))


@admin.command('add-user',
               short_help=('Adds an AWS user to the group permitted '
                           'to perform the db migration'))
@click.argument('username')
@pass_admin_session
def add_user(session, username):
    iam = session.resource('iam')
    try:
        user = awsiam.ensure_user(iam, username)
    except ClientError as err:
        util.echo_error(str(err))
        click.secho('New users must be added manually '
                    'via the AWS cli or web console',
                    underline=True)
    else:
        logger.info('User {} ({}) is configured for database migration',
                    user.name,
                    user.arn)


@admin.command('list-users',
               short_help='Lists users of the db migration group')
@util.option('--verify/--no-verify',
             default=True,
             help='Switch to check if users are correctly configured.')
@pass_admin_session
def list_users(session, verify):
    """Display the IAM accounts allowed to perform the migrate.

    (Require admin privileges)
    """
    iam = session.resource('iam')
    aws_meta = session.aws_meta
    (users, errors) = awsiam.users(iam,
                                   aws_meta.assume_role_policy_name,
                                   role_name=aws_meta.role_name,
                                   group_name=aws_meta.group_name,
                                   verify=verify)
    if errors:
        ctx = click.get_current_context()
        msg = 'Hint: run "{.info_name} setup" to fix all errors :)'
        util.echo_info(msg.format(ctx.parent), underline=True)
    click.secho(json.dumps(users, indent=True, sort_keys=True), fg='cyan')


@admin.command('sync-users', short_help='Synchronizes all migration-users')
@pass_admin_session
def sync_users(session):
    iam = session.resource('iam')
    aws_meta = session.aws_meta
    group_name = aws_meta.group_name
    util.echo_waiting('Syncing members of group {} ... '.format(group_name))
    awsiam.sync_migration_users(iam,
                                aws_meta.assume_role_policy_name,
                                role_name=aws_meta.role_name,
                                group_name=group_name)
    util.echo_sig('done')


cli = admin(obj={})
