import base64
import configparser
import functools
import json
import operator
import os
import pickle
import pprint
import sys

from botocore.exceptions import ClientError
import boto3
import click

BUILD_STATE_PATH = os.path.join(os.getcwd(), '.build-state')
IAM_ASSUME_ROLE_NAME = 'wb-build-db-assume'
IAM_ASSUME_POLICY_NAME = 'wb-build-db-assume'
IAM_DB_BUILD_GROUP = 'wb-db-builders'
IAM_DB_BUILD_ROLE = 'wb-build-db'
KEY_PAIR_PATH = os.getcwd()
LOCAL_ASSUME_ROLE_PROFILE = 'wb-db-builder'
ROLE_SESSION_NAME = LOCAL_ASSUME_ROLE_PROFILE + '_assumed'

# XXX: Danger: These names could be changed in the AWS console.
IAM_DB_BUILD_POLICIES = (
    'DecodeAuthorizationMessages',
    'IAMReadOnlyAccess',
    'ec2-manage-instances',
    'ec2-manage-keypairs-and-security-groups',
    'ec2-manage-volumes'
    'ec2-run-db-build-instance',
    'ec2-tagging',
    's3-datomic-backups-full-access',
)

IAM_ASSUME_POLICY_STMT_TEMPLATE = {
    "Effect": "Allow",
    "Action": "sts:AssumeRole"
}

USER_DATA = """#cloud-config
repo_update: true
repo_upgrade: all

packages:
  - java-1.8.0-openjdk-headless
  - python34

runcmd:
  - touch /tmp/test.txt
  - [su, -c, ec2-user, ""]
"""    

echo = click.echo
echo_error = functools.partial(click.secho, fg='red', bg='white')
echo_info = functools.partial(click.secho, fg='blue')
echo_header = functools.partial(click.secho, fg='green')


def _make_asssume_role_policy(version='2012-10-17', **kw):
    pol_stmt = dict(IAM_ASSUME_POLICY_STMT_TEMPLATE, **kw)
    return dict(Version=version, Statement=[pol_stmt])
    
def _get_assuming_aws_username(session):
    """Return a role-id:role_session_name as per AWS documentation.

    See table entry under:
      "Request Information That You Can Use for Policy Variables"

    http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_variables.html#policy-vars-formoreinfo
    """
    profile_name = session.profile_name
    conf = session._session.full_config['profiles'][profile_name]
    role_name = conf['role_arn'].rsplit('/')[1]
    iam = session.resource('iam')
    role = iam.Role(role_name)
    format_aws_userid = '{role.role_id}:{conf[role_session_name]}'.format
    return format_aws_userid(role=role, conf=conf)


def get_key_pair(ec2, release):
    key_pair_name = 'db-build-{}-keypair'.format(release)
    try:
        key_pair = ec2.KeyPair(key_pair_name)
        key_pair.load()
    except ClientError:
        echo_info('KeyPair {} already exists, '
                  'create new one.'.format(key_pair_name))
        key_pair = ec2.create_key_pair(KeyName=key_pair_name)
        key_pair_path = os.path.join(KEY_PAIR_PATH, key_pair_name)
        with open(key_pair_path, 'wb') as fp:
            fp.write(key_pair.key_material.encode('ascii'))
        os.chmod(fp.name, 0o600)
    return key_pair


def dump_build_state(state):
    with open(BUILD_STATE_PATH, 'wb') as fp:
        pickle.dump(state, fp)

def load_build_state():
    try:
        with open(BUILD_STATE_PATH, 'rb') as fp:
            state = pickle.load(fp)
    except IOError:
        state = {}
    return state


def _report_status(instance):
    echo_info('Instance Id: '
              '{0.instance_id}'.format(instance))
    echo_info('Instance Type: '
              '{0.instance_type}'.format(instance))
    echo_info('Instance Public DNS name: '
              '{0.public_dns_name}'.format(instance))
    echo_info('Instance Public IP Address: '
              '{0.public_ip_address}'.format(instance))
    echo_info('Tags: {}'.format(instance.tags))
    echo_info('Launched at: ' +
              instance.launch_time.isoformat(' '))


def _ensure_group(session, iam, group_name):
    group = iam.Group(group_name)
    try:
        group.load()
    except ClientError:
        echo_error(
            'AWS IAM Group {!r} does not exist.'.format(group_name))
        # XXX: Use click's exit() method
        sys.exit(1)
        
    users = list(group.users.all())
    if not users:
        raise Exception('No users added to the "{}" '
                        'AWS IAM group {}'.format(group_name))
    return group

def _ensure_role(session, iam, assume_role_name, group):
    role_map = {role.name: role for role in iam.roles.all()}
    role = role_map.get(assume_role_name)

    user_arns = list(user.arn for user in group.users.all())
    arp_doc = _make_asssume_role_policy(Principal=dict(AWS=user_arns))
    if role is None:
        role = iam.create_role(
            RoleName=assume_role_name,
            AssumeRolePolicyDocument=json.dumps(arp_doc))
    else:
        arp = role.AssumeRolePolicy()
        arp.update(arp_doc)
    return role


def _ensure_assume_role_policy(session, iam, role, policy_name):
    pol_map = {pol.policy_name: pol
               for pol in iam.policies.filter(Scope='Local').all()}
    pol = pol_map.get(policy_name)
    if pol is None:
        policy_doc = _make_asssume_role_policy(Resource=role.arn)
        iam.create_policy(
            PolicyName=policy_name,
            Path='/',
            PolicyDocument=policy_doc,
            Description=('Allows the IAM user to which this policy '
                         'is attached to assume '
                         'the {role.name} role.'.format(role=role)))
    return pol


def _ensure_set(config_parser, section, opt, new_value):
    val = config_parser.get(section, opt, fallback=None)
    if val != new_value:
        config_parser.set(section, opt, new_value)

def _ensure_config(session, role):
    p_session = session._session
    cp = configparser.ConfigParser()
    config_file = p_session.get_config_variable('config_file')
    config_path = os.path.expanduser(config_file)
    cp.read(config_path)

    section = 'profile ' + LOCAL_ASSUME_ROLE_PROFILE
    if section not in set(cp.sections()):
        cp.add_section(section)

    ensure_set = functools.partial(_ensure_set, cp, section)
    ensure_set('region', session.region_name)
    ensure_set('role_arn', role.arn)
    ensure_set('source_profile', session.profile_name)
    ensure_set('role_session_name', ROLE_SESSION_NAME)

    with open(config_path, 'w') as fp:
        cp.write(fp)
    

@click.group()
@click.option('--profile',
              default='default',
              help='AWS profile')
@click.pass_context
def build(ctx, profile):
    ctx.obj['profile'] = profile
    ctx.obj['session'] = boto3.Session(profile_name=profile)


@build.command()
@click.option('--group-name',
              default=IAM_DB_BUILD_GROUP,
              help=('Name of the AWS IAM group '
                    'that contains users permitted '
                    'to perform the build.'))
@click.option('--assume-role-name',
              default=IAM_ASSUME_ROLE_NAME,
              help=('The name of the role that users of '
                    'the builders group use in order to assume role'))
@click.pass_context
def list_users(ctx, group_name, assume_role_name):
    """Display the IAM accounts allowed to perform the build.

    (Require admin privileges)
    """
    session = ctx.obj['session']
    iam = session.resource('iam')
    group = iam.Group(group_name)
    group.load()
    data = {'users':[]}
    for user in sorted(group.users.all(), key=operator.attrgetter('name')):
        data['users'].append(dict(name=user.name, arn=user.arn))
    click.echo(json.dumps(data, indent=True))


@build.command()
@click.argument('assume_role_name')
@click.option('--iam-group-name',
              default=IAM_DB_BUILD_GROUP,
              help='Default IAM group for build users')
@click.pass_context
def setup_iam(ctx, assume_role_name):
    session =  ctx.obj['session']
    iam = session.resource('iam')
    abort = ctx.abort
    try:
        group = _ensure_group(session, iam, IAM_DB_BUILD_GROUP)
        role = _ensure_role(session, iam, assume_role_name, group)
        _ensure_config(session, iam, role)
        _ensure_assume_policy(session, iam, role)
    except Exception as e:
        abort(e)
    click.secho('Good to go!', fg='green')


@build.command()
@click.option('--dry-run',
              default=False,
              help='Test to see if this command would execute.')
@click.option('--iam-instance-profile-arn',
              default=('arn:aws:iam::357210185381:instance-profile/'
                       'wb-db-build-instance-profile'),
              help="""\
The ARN (Amazon Resource Name) of the instance profile used for the build.
This isinstance profile is associated with IAM role assumed by regular users
in order to perform administrative operations required for the build.
              """)
@click.option('--ami',
              # latest Amazon AMI (us-east-1, EBS-backed, 64-bit)
              default='ami-8ff710e2',
              help='Amazon AMI Identifier')
@click.option('--monitoring',
              type=bool,
              default=True,
              help='Whether or not the instance has monitoring enabled.')
@click.option('--instance-type',
              default='t1.micro',
              help='AWS EC2 Instance Type')
@click.argument('release')
@click.pass_context
def kick_off(ctx,
             release,
             ami,
             monitoring,
             iam_instance_profile_arn, # XXX: remove?
             instance_type,
             dry_run):
    """Start the build."""
    state = {}
    session = ctx.obj['session']
    ec2 = session.resource('ec2')
    key_pair = get_key_pair(ec2, release)
    instance_options = dict(
        ImageId=ami,
        InstanceType=instance_type,
        KeyName=key_pair.name,
        MinCount=1,
        MaxCount=1,
        UserData=base64.b64encode(USER_DATA.encode('ascii')),
        Monitoring=dict(Enabled=monitoring),
        DryRun=dry_run)
    instances = ec2.create_instances(**instance_options)
    instance = instances[0]
    aws_username = _get_assuming_aws_username(session)
    instance.create_tags(Tags=[
        dict(Key='CreatedBy', Value=aws_username)])
    state['release'] = release
    state['aws_profile_assumed'] = session.profile_name
    state['aws_profile_assuming'] = aws_username
    state['instance-options'] = instance_options
    state['instance'] = dict(id=instance.id,
                             KeyPairName=key_pair.name)
    click.echo('Waiting for instance to start... ', nl=False)
    instance.wait_until_running()
    click.secho('done', fg='green')
    _report_status(instance)
    dump_build_state(state)


@build.command()
@click.pass_context
def destroy(ctx):
    state = load_build_state()
    session = ctx.obj['session']
    ec2 = session.resource('ec2')
    instance_id = state['instance']['id']
    instances = ec2.instances.filter(InstanceIds=[instance_id])
    instance = next(iter(instances))
    instance.terminate()


@build.command()
@click.pass_context
def show_state(ctx):
    echo('Build state:')
    echo_info(pprint.pformat(load_build_state()))


if __name__ == '__main__':
    build(obj={})
    
    
