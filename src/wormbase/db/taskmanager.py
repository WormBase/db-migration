# -*- coding: utf-8 -*-
import base64
import contextlib
import os
import pprint
import re
import socket
import time

from botocore.exceptions import ClientError
from pkg_resources import resource_filename
from scp import SCPClient
import click

from . import awsiam
from . import log
from . import ssh
from . import util


USER_DATA_PATH = resource_filename(
    __package__,
    'cloud-config/AWS-cloud-config-UserData.template')

# Instance settings based on image of default Amazon AMI (ami-f5f41398, 2016)
EC2_INSTANCE_DEFAULTS = dict(
    ami='ami-1517ee78',
    instance_type='r3.4xlarge',
    monitoring=True,
    dry_run=False)

EC2_INSTANCE_ROLE = 'development'

logger = log.get_logger(__name__)


def load_ec2_instance_from_state(ctx, state):
    session = ctx.obj['session']
    ec2 = session.resource('ec2')
    instance = ec2.Instance(state['id'])
    instance.load()
    return instance


def wait_for_sshd(ec2_instance, max_timeout=60 * 6):
    waited = 0
    wait_msg = 'Waiting for connectivity to instance {.id}... '
    wait_msg = wait_msg.format(ec2_instance)
    while True:
        util.echo_waiting(wait_msg)
        s = socket.socket()
        s.settimeout(20)
        try:
            s.connect((ec2_instance.public_dns_name, 22))
            util.echo_sig('connected')
            break
        except Exception:
            time.sleep(20)
            waited += 40
        if waited >= max_timeout:
            msg = 'Failed to connect via ssh to {.public_dns_name}'
            msg = msg.format(ec2_instance)
            raise socket.timeout(msg)
        else:
            util.echo_retry('not yet, retrying')
    # To be sure...
    time.sleep(1)


@contextlib.contextmanager
def latest_migration_state(ctx):
    bstate = ctx.obj['db-mig-state']
    bstate.sync()
    curr_bstate = bstate.get('current')
    if curr_bstate is None:
        util.echo_error('No current instance to terminate.')
        util.echo_info('Other instances may be running, '
                       'use the AWS web console or CLI')
        ctx.abort()
    try:
        instance = load_ec2_instance_from_state(ctx, curr_bstate)
        instance_state = dict(instance.state)
    except (ClientError, AttributeError):
        instance_state = dict(Name='terminated?', code='<unknown>')
    curr_bstate['instance-state'] = instance_state
    yield (instance, curr_bstate)


def get_archive_filename():
    # XXX: Path to filename produced by: python setup.py sdist (for now)
    # XXX: Best to download from github release.
    pkg_fullname = util.distribution_name()
    archive_filename = pkg_fullname + '.tar.gz'
    return archive_filename


def bootstrap(ec2_instance, package_version):
    """Deploy this package to the AWS instance.

    This involves scp'ing the data due to the repo being private.
    If, in the future this repo is deemed ok to be public,
    then this bootstraping via scp can be eliminated and
    commands run in UserData to fetch and install the data
    directly from a github release.

    This also requires the system package 'python3-dev'.
    """
    finished_regex = re.compile(r'Cloud-init.*finished')
    archive_filename = get_archive_filename()
    path = os.path.join('dist', archive_filename)
    util.local('python setup.py sdist')

    # Wait for cloud-init/config process to finish
    while True:
        with ssh.connection(ec2_instance) as conn:
            out = ssh.exec_command(
                conn,
                'tail -n1 /var/log/cloud-init-output.log')
        last_line = out.rstrip()
        if finished_regex.match(last_line) is not None:
            break
        time.sleep(30)

    # Upload the tar file
    with ssh.connection(ec2_instance) as conn:
        with SCPClient(conn.get_transport()) as scp:
            scp.put(path, archive_filename)

    # Now the wormbase-db-migrate package dependencies are available
    # and installation can proceed
    pip_install = 'python3 -m pip install --user '
    wbdb_install_cmd = pip_install + archive_filename
    pip_install_cmds = [pip_install + ' --upgrade pip',
                        wbdb_install_cmd]
    with ssh.connection(ec2_instance) as conn:
        for cmd in pip_install_cmds:
            try:
                out = ssh.exec_command(conn, cmd)
            except Exception:
                logger.exception()
            else:
                logger.debug(out)


def aws_userid(session):
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
    role.load()
    format_aws_userid = '{role.role_id}:{conf[role_session_name]}'.format
    return format_aws_userid(role=role, conf=conf)


def report_status(instance):
    if instance.meta.data is None:
        logger.info('No instance status to report.')
        return
    instance_state = instance.state.get('Name')
    is_active = instance_state != 'terminated'
    status = instance_state if is_active else 'terminated'
    logger.info('Instance Id: ' '{}', instance.id)
    logger.info('Tags: {}', instance.tags)
    logger.info('Launched at: ' + instance.launch_time.isoformat(' '))
    logger.info('Status: {}', status)
    if is_active:
        logger.info('Instance Type: {}', instance.instance_type)
        logger.info('Instance Public DNS name: {}', instance.public_dns_name)
        logger.info('Instance Public IP Address: {}',
                    instance.public_ip_address)


@util.command_group()
@util.log_level_option(default='INFO')
@util.option('--profile',
             default='default',
             help='AWS profile')
@util.option('--assume-role',
             default=awsiam.DB_MIG_ROLE,
             help='AWS Role that will be assumed to execute the migrate')
@click.pass_context
def tasks(ctx, log_level, profile, assume_role):
    log.setup_logging(log_level=log_level)
    ctx.obj['profile'] = profile
    session = awsiam.make_session(profile_name=profile)
    iam = session.resource('iam')
    role = iam.Role(assume_role)
    role.load()
    (profile_name, ar_profile_name) = awsiam.ensure_config(ctx, session, role)
    if ar_profile_name is not None:
        profiles = session._session.full_config['profiles']
        ar_profile = profiles[ar_profile_name]
        try:
            session = awsiam.make_session(profile_name)
        except ClientError:
            pass
        else:
            ctx.obj['assumed_role'] = ar_profile['role_arn']
    ctx.obj['session'] = session
    ctx.obj['db-mig-state'] = util.aws_state()


@tasks.command(short_help='Start the migrate process')
@util.option('--wb-db-migrate-version',
             default='0.1',
             help='The version of *this* python package')
@util.option('--dry-run',
             type=bool,
             default=False,
             help='Test to see if this command would execute.')
@util.option('--ami',
             # latest Amazon AMI (us-east-1, EBS-backed, 64-bit)
             default=EC2_INSTANCE_DEFAULTS['ami'],
             help='Amazon AMI Identifier. ')
@util.option('--monitoring',
             type=bool,
             default=True,
             help='Whether or not the instance has monitoring enabled.')
@util.option('--instance-type',
             default=EC2_INSTANCE_DEFAULTS['instance_type'],
             help='AWS EC2 Instance Type ')
@util.option('--keypair-name',
             default='wb-db-migrate',
             help='Name of EC2 KeyPair.')
@click.argument('sdist_path', metavar='<sdist>')
@click.argument('ws_data_release', metavar='<WSXXX data release>')
@click.pass_context
def init(ctx,
         sdist_path,
         ws_data_release,
         wb_db_migrate_version,
         ami,
         monitoring,
         instance_type,
         keypair_name,
         dry_run):
    """Start the migrate."""
    session = ctx.obj['session']
    state = ctx.obj['db-mig-state']
    ec2 = session.resource('ec2')
    key_pair = ssh.recycle_key_pair(ec2, keypair_name)
    with open(USER_DATA_PATH) as fp:
        user_data = fp.read()
    instance_options = dict(
        ImageId=ami,
        InstanceType=instance_type,
        KeyName=key_pair.name,
        MinCount=1,
        MaxCount=1,
        UserData=base64.b64encode(user_data.encode('utf-8')),
        Monitoring=dict(Enabled=monitoring),
        DryRun=dry_run)
    created_by = aws_userid(session)
    instances = ec2.create_instances(**instance_options)
    instance = next(iter(instances))
    instance.create_tags(Tags=[
        dict(Key='CreatedBy', Value=created_by),
        dict(Key='Name', Value='wb-db-migrate-experimental'),
        dict(Key='Role', Value=EC2_INSTANCE_ROLE)])
    state[instance.id] = dict(id=instance.id,
                              init_options=instance_options,
                              KeyPairName=key_pair.name,
                              public_dns_name=instance.public_dns_name,
                              public_ip_addr=instance.public_ip_address,
                              started_by=session.profile_name,
                              ws_data_release=ws_data_release)
    state['current'] = state[instance.id]
    util.echo_waiting('Waiting for instance to enter running state ... ')
    instance.wait_until_running()
    util.echo_sig('done')
    wait_for_sshd(instance)
    util.echo_waiting('Bootstrapping instance with wormbase.db')
    bootstrap(instance, wb_db_migrate_version)
    util.echo_sig('done')
    report_status(instance)

    # XXX: DEBUG
    msg = 'ssh -i {0.key_pair.name} -l ec2-user {0.public_dns_name}'
    logger.info(msg.format(instance))

    state['instance-state'] = dict(instance.state)
    return state


@tasks.command(short_help='Terminate ephemeral EC2 resources')
@click.pass_context
def terminate(ctx):
    with latest_migration_state(ctx) as (instance, state):
        try:
            instance.terminate()
        except ClientError as client_error:
            msg = ('Only {[started-by]} or an adminstrator '
                   'will be able to terminate the instance')
            msg = msg.format(state)
            click.secho(str(client_error), fg='red')
            util.echo_error(msg)
        finally:
            state['instance-state'] = instance.state
        msg = 'Instance {.id!r} is {[Name]}'
        util.echo_info(msg.format(instance, instance.state))


@tasks.command('view-state',
               short_help='Describe the state of the instance.')
@click.pass_context
def view_state(ctx):
    with latest_migration_state(ctx) as (_, state):
        util.echo_info(pprint.pformat(state))


@tasks.command(short_help='Describes the status of the instance.')
@click.pass_context
def status(ctx):
    with latest_migration_state(ctx) as (instance, _):
        report_status(instance)


cli = tasks(obj={})
