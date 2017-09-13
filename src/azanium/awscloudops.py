# -*- coding: utf-8 -*-
import base64
import contextlib
import mimetypes
import operator
import os
import pprint
import re
import socket
import time

from botocore.exceptions import ClientError
from pkg_resources import resource_filename
from scp import SCPClient
import click
import configobj

from . import awsiam
from . import config
from . import github
from . import log
from . import root_command
from . import ssh
from . import util
from .admin import admin


USER_DATA_PATH = resource_filename(
    __package__,
    'cloud-config/AWS-cloud-config-UserData.template')

# Instance settings based on image of default Amazon AMI (ami-f5f41398, 2016)
EC2_INSTANCE_DEFAULTS = dict(
    ami='ami-6869aa05',
    instance_type='m4.4xlarge',
    monitoring=True,
    dry_run=False)

BLOCK_DEVICE_MAPPINGS = [{
    # 50Gb for root
    'DeviceName': '/dev/xvda',
    'Ebs': {
        'VolumeSize': 50,
        'VolumeType': 'gp2',
        'DeleteOnTermination': False
    },
}, {
    # 500Gb for data
    'DeviceName': '/dev/xvdb',
    'Ebs': {
        'VolumeSize': 500,
        'VolumeType': 'gp2',
        'DeleteOnTermination': False
    }
}]

logger = log.get_logger(namespace=__name__)


def load_ec2_instance_from_state(ctx, state):
    session = ctx.session
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
    bstate = ctx.db_mig_state
    bstate.sync()
    curr_bstate = bstate.get('current')
    if curr_bstate is None:
        logger.error('No current instance to terminate.')
        logger.info('Other instances may be running, '
                    'use the AWS web console or CLI')
        click.get_current_context().exit()
    try:
        instance = load_ec2_instance_from_state(ctx, curr_bstate)
        instance_state = dict(instance.state)
    except (ClientError, AttributeError):
        instance_state = dict(Name='terminated?', code='<unknown>')
    curr_bstate['instance-state'] = instance_state
    yield (instance, curr_bstate)


def get_archive_filename():
    pkg_fullname = util.distribution_name()
    archive_filename = pkg_fullname + '.tar.gz'
    return archive_filename


def deploy_aws_config(ctx, ec2_instance):
    session = ctx.session
    aws_conf_dir = '~/.aws'
    copy_config_file = awsiam.copy_config_file
    conf_filename = os.path.basename(config.PATH)
    aws_config_2_copy = (
        ('credentials', [ctx.user_profile]),
        ('config', [
            awsiam.profile_key(ctx.user_profile),
            'profile ' + ctx.assumed_profile])
    )
    with ssh.connection(ec2_instance) as conn:
        ssh.exec_command(conn, 'mkdir ' + aws_conf_dir)
        with SCPClient(conn.get_transport()) as scp:
            scp.put(config.PATH, conf_filename)
            for (artefact, keys) in aws_config_2_copy:
                with copy_config_file(session, artefact, keys) as tmp_path:
                    remote_conf_path = os.path.join(aws_conf_dir, artefact)
                    scp.put(tmp_path, remote_conf_path)


def deploy_myself(ctx, ec2_instance, dev_mode=False):
    pip_install = 'python3 -m pip install --user '
    pip_install_cmds = [pip_install + ' --upgrade pip']
    if dev_mode:
        util.local('python setup.py sdist')
        archive_filename = util.distribution_name() + '.tar.gz'
        with ssh.connection(ec2_instance) as conn:
            with SCPClient(conn.get_transport()) as scp:
                scp.put('dist/' + archive_filename, archive_filename)
        pip_install_cmds.append(pip_install + archive_filename)
    else:
        repo = github.infer_from_local_repo()
        release_asset = next(repo.latest_release().assets(), None)
        if release_asset is None:
            raise EnvironmentError('Could not find latest release of ' +
                                   __package__)
        github_release_url = release_asset.browser_download_url
        pip_install_cmds.append(pip_install + github_release_url)
    with ssh.connection(ec2_instance) as conn:
        for cmd in pip_install_cmds:
            try:
                out = ssh.exec_command(conn, cmd)
            except Exception as e:
                logger.exception(str(e))
            else:
                logger.debug(out)


def bootstrap(ctx, ec2_instance, package_version, dev_mode=False):
    """Deploy this package to the AWS instance.

    This involves scp'ing the data due to the repo being private.
    If, in the future this repo is deemed ok to be public,
    then this bootstraping via scp can be eliminated and
    commands run in UserData to fetch and install the data
    directly from a github release.

    This also requires the system package 'python3-dev'.
    """
    finished_regex = re.compile(r'Cloud-init.*finished')

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

    deploy_aws_config(ctx, ec2_instance)
    deploy_myself(ctx, ec2_instance, dev_mode=dev_mode)


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
    logger.debug('Instance Id: ' '{}', instance.id)
    logger.debug('Tags: {}', instance.tags)
    logger.debug('Launched at: ' + instance.launch_time.isoformat(' '))
    if is_active:
        logger.debug('Instance Type: {}', instance.instance_type)
        logger.debug('Instance Public DNS name: {}', instance.public_dns_name)
        logger.debug('Instance Public IP Address: {}',
                     instance.public_ip_address)
    logger.info('Instance is {}', status.capitalize())


@root_command.group()
@util.pass_command_context
def cloud(ctx):
    """AWS EC2 operations for the WormBase database migration."""
    pass


def _tag_resources(session, instance):
    created_by = aws_userid(session)
    created_by_tag = dict(Key='CreatedBy', Value=created_by)
    role_tag = dict(Key='Role', Value='database-migration')
    instance.create_tags(Tags=[
        created_by_tag,
        dict(Key='Name', Value='wb-db-migration'),
        role_tag])

    ebs_volumes = sorted(instance.volumes.all(),
                         key=operator.attrgetter('size'))
    volumes = iter(ebs_volumes)
    root_volume = next(volumes)
    root_volume.create_tags(Tags=[created_by_tag,
                                  dict(Key='Name', Value='DB Migration Root'),
                                  role_tag])
    data_volume = next(volumes)
    data_volume.create_tags(Tags=[created_by_tag,
                                  dict(Key='Name', Value='DB Migration Data'),
                                  role_tag])


@admin.command('create-instance',
               short_help='Create an instance to be used for DB migration')
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
@util.option('--dev-mode/--no-dev-mode',
             default=False,
             help=('In dev-mode, use local state git repository for deploying azanium/'
                   'In no-dev-mode, will use the latest release from github'))
@click.argument('ws_data_release', metavar='<WSXXX data release>')
@click.argument('subnet_id', metavar='<EC2-VPC subnet-id>')
@click.argument('security_group_id', metavar='<EC2-VPC security-group-id>')
@util.pass_command_context
def create_instance(ctx,
                    ws_data_release,
                    wb_db_migrate_version,
                    subnet_id,
                    security_group_id,
                    ami,
                    monitoring,
                    instance_type,
                    keypair_name,
                    dry_run,
                    dev_mode):
    """Start the migrate."""
    session = ctx.session
    state = ctx.db_mig_state
    ec2 = session.resource('ec2')
    if not os.path.isfile(config.PATH):
        util.echo_error('azanium is not configured, run:', notify=False)
        util.echo_error('\tazanium configure', notify=False)
        click.get_current_context().abort()
    (key_pair, key_pair_path) = ssh.recycle_key_pair(ec2, keypair_name)
    with open(USER_DATA_PATH) as fp:
        user_data = fp.read()
        completion_script = util.pkgpath('completion/azanium-complete.sh')
        user_data %= {
            'azanium_completion_script': completion_script
        }
    instance_options = dict(
        ImageId=ami,
        InstanceType=instance_type,
        KeyName=key_pair.name,
        SubnetId=subnet_id,
        BlockDeviceMappings=BLOCK_DEVICE_MAPPINGS,
        MinCount=1,
        MaxCount=1,
        UserData=base64.b64encode(user_data.encode('utf-8')),
        Monitoring=dict(Enabled=monitoring),
        SecurityGroupIds=[security_group_id],
        EbsOptimized=True,  # XXX: This is dependent on instance type
        DryRun=dry_run)
    instances = ec2.create_instances(**instance_options)
    instance = next(iter(instances))
    _tag_resources(session, instance)
    state[instance.id] = dict(id=instance.id,
                              init_options=instance_options,
                              KeyPairName=key_pair.name,
                              public_dns_name=instance.public_dns_name,
                              public_ip_addr=instance.public_ip_address,
                              started_by=ctx.user_profile,
                              ws_data_release=ws_data_release)
    state['current'] = state[instance.id]
    util.echo_waiting('Waiting for instance to enter running state ... ')
    instance.wait_until_running()
    util.echo_sig('done')
    wait_for_sshd(instance)
    util.echo_waiting(
        'Bootstrapping instance with {}'.format(__package__))
    bootstrap(ctx, instance, wb_db_migrate_version, dev_mode=dev_mode)
    util.echo_sig('done')
    report_status(instance)
    msg = 'ssh -i {} -l ec2-user {}'
    logger.info(msg.format(key_pair_path, instance.public_dns_name))
    state['instance-state'] = dict(instance.state)
    return state


@admin.command('instance-state',
               short_help='Describe the state of the instance.')
@util.pass_command_context
def view_instance_state(ctx):
    with latest_migration_state(ctx) as (_, state):
        util.echo_info(pprint.pformat(state))


@admin.command('instance-status',
               short_help='Describes the status of the instance.')
@util.pass_command_context
def instance_status(ctx):
    with latest_migration_state(ctx) as (instance, _):
        report_status(instance)


@cloud.command('upload-file',
               short_help='Upload a file to a db-migration folder on s3')
@util.option('-b', '--bucket-name',
             default='wormbase',
             help='Name of the S3 bucket')
@util.pass_command_context
@click.argument('path_to_upload')
@click.argument('path_in_bucket')
def upload_file(ctx, path_to_upload, path_in_bucket, bucket_name):
    session = ctx.session
    s3 = session.resource('s3')
    key = path_in_bucket
    bucket = s3.Bucket(bucket_name)
    config_path = awsiam.get_conf_var(session, 'config_file')
    conf = configobj.ConfigObj(config_path)
    role_arn = conf['profile ' + ctx.assumed_profile]['role_arn']
    extra_args = {
        'Metadata': {
            'CreatedBy': ctx.user_profile,
            'AssumedRole': role_arn.rsplit('/', 1)[-1]
        },
        'ACL': 'public-read'
    }
    ct_match = mimetypes.guess_type(path_to_upload)
    if all(ct_match):
        content_type = ct_match[0]
    else:
        content_type = 'text/plain'
    extra_args['ContentType'] = content_type
    try:
        logger.debug('{} (assumed role:{}) '
                     'is attempting to upload {} to s3://{}/{}',
                     ctx.user_profile,
                     ctx.assumed_profile,
                     path_to_upload,
                     bucket_name,
                     key)
        bucket.upload_file(path_to_upload, key, ExtraArgs=extra_args)
    except ClientError as client_err:
        logger.exception(str(client_err))
        click.get_current_context().exit()
    else:
        url = 'https://s3.amazonaws.com/{}/{}'.format(bucket.name, key)
        logger.info('Uploaded {} to {}', path_to_upload, url)
    return url
