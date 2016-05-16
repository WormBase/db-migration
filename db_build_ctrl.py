import operator
import os
import subprocess

import boto3
import click


IAM_BUILD_GROUP = 'wb-db-builders'
IAM_ASSUME_BUILD_ROLE = 'wb-db-build-assume-role'

AWS_CONFIG_PATH = os.environ.get(
    'AWS_CONFIG_FILE',
    os.path.expanduser('~/.aws/config'))


def terraform(cmd):
    cmd_parts = ['terraform'] + cmd.split()
    return subprocess.call(cmd_parts)
    

# Only for use by an admin!
def get_build_user_arns(iam, group_name):
    groups = {group.name: group
              for group in iam.groups.all()}
    return groups[group_name].users.all()

@click.group()
@click.option('--profile',
              default='default',
              help='AWS profile')
@click.pass_context
def build(ctx, profile):
    ctx.obj['profile'] = profile

@build.command()
@click.option('--builders-group',
              default='wb-db-builders',
              help=('Name of the AWS IAM group '
                    'that contains users permitted '
                    'to perform the build.'))
@click.option('--role-to-assume',
              default='wb-db-build-assume-role',
              help=('The name of the role that users of '
                    'the builders group use in order to assume role'))
@click.pass_context
def show_build_users(ctx, builders_group, role_to_assume):
    """Display the IAM accounts allowed to perform the build.

    (Require admin privileges)
    """
    session = boto3.Session(profile_name=ctx.obj['profile'])
    iam = session.resource('iam')
    users = get_build_user_arns(iam, builders_group)
    # import pdb; pdb.set_trace()
    print('The following users can perform the build:')
    for user in sorted(users, key=operator.attrgetter('name')):
        s = 'Name: {user.name} (ARN={user.arn})'
        click.echo(s.format(user=user))


@build.command()
@click.pass_context
def kick_off(ctx):
    """Start the build."""
    terraform('plan')



if __name__ == '__main__':
    build(obj={})
    
    
