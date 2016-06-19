import contextlib
import functools
import json
import operator
import os
import tempfile

import boto3
import click
import configobj
from botocore.exceptions import ClientError
from botocore.exceptions import ProfileNotFound

from .log import get_logger


DB_MIG_GROUP = 'wb-db-migration-users'

DB_MIG_ROLE = 'wb-db-migrator'

DB_MIG_GROUP_POLICIES = {
    'IAMReadOnlyAccess',
}

DB_MIG_ROLE_POLICIES = {
    'DecodeAuthorizationMessages',
    'IAMReadOnlyAccess',
    'ec2-manage-instances',
    'ec2-manage-keypairs-and-security-groups',
    'ec2-manage-volumes'
    'ec2-run-db-migration-instances',
    'ec2-tagging',
    's3-datomic-backups-full-access'
}

logger = get_logger(namespace=__name__)


def make_session(profile_name):
    try:
        sess = boto3.Session(profile_name=profile_name)
    except ProfileNotFound as pnf:
        logger.error(str(pnf))
        click.get_current_context().abort()
    return sess


def ensure_set(config, section, opt, new_value):
    val = config.get(section, opt)
    if val != new_value:
        opts = config[section]
        opts[opt] = new_value
        return True
    return False


def ensure_config(ctx, session, role):
    assume_role_profile_name = '{.name}-assumer'.format(role)
    p_session = session._session
    config_file = p_session.get_config_variable('config_file')
    config_path = os.path.expanduser(config_file)
    config = configobj.ConfigObj(config_path, raise_errors=True)
    section = 'profile ' + assume_role_profile_name
    if section not in set(config):
        config.setdefault(section, {})
    ensure_set_val = functools.partial(ensure_set, config, section)
    changes = []
    for (prop, val) in [('region', session.region_name),
                        ('role_arn', role.arn),
                        ('source_profile', session.profile_name),
                        ('role_session_name', '{.name}-assumed'.format(role))]:
        changes.append(ensure_set_val(prop, val))
    if any(changes):
        config.write()
    try:
        sess = make_session(assume_role_profile_name)
        sess.resource('iam')
        profile_name = assume_role_profile_name
    except ClientError:
        del config[section]['source_profile']
        config.write()
        profile_name = None
    return (sess.profile_name, profile_name)


def get_conf_var(session, varname):
    return os.path.expanduser(session._session.get_config_variable(varname))


@contextlib.contextmanager
def copy_config_file(session, artefact, keys):
    src = configobj.ConfigObj(get_conf_var(session, artefact + '_file'))
    fn_suffix = 'aws-' + artefact + '-copy'
    with tempfile.NamedTemporaryFile(suffix=fn_suffix) as fp:
        dest = configobj.ConfigObj(fp.name)
        for key in keys:
            dest[key] = src[key]
        dest['default'] = dest[keys[0]]
        dest.write()
        yield fp.name


def ensure_role(iam,
                role_name=DB_MIG_ROLE,
                role_policies=DB_MIG_ROLE_POLICIES,
                group_name=DB_MIG_GROUP):
    role = iam.Role(role_name)
    group = iam.Group(group_name)
    user_arns = list(user.arn for user in group.users.all())
    arp_doc = make_asssume_role_policy(Principal=dict(AWS=user_arns))
    if role is None:
        role = iam.create_role(RoleName=role_name,
                               AssumeRolePolicyDocument=json.dumps(arp_doc))
    else:
        arp = role.AssumeRolePolicy()
        arp.update(PolicyDocument=json.dumps(arp_doc))
    role_policy_names = set(role_policies)
    for policy in iam.policies.all():
        if policy.policy_name in role_policy_names:
            role.attach_policy(PolicyArn=policy.arn)
    return role


def get_policy_by_name(iam, policy_name):
    pol_map = {pol.policy_name: pol
               for pol in iam.policies.filter(Scope='Local').all()}
    pol = pol_map.get(policy_name)
    return pol


def make_asssume_role_policy(version='2012-10-17', **pol_stmt_attrs):
    pol_stmt_attrs.setdefault('Effect', 'Allow')
    pol_stmt_attrs.setdefault('Action', 'sts:AssumeRole')
    pol_stmt = dict(pol_stmt_attrs)
    return dict(Version=version, Statement=[pol_stmt])


def ensure_assume_role_policy(iam, role, policy_name):
    pol = get_policy_by_name(iam, policy_name)
    if pol is None:
        policy_doc = make_asssume_role_policy(Resource=role.arn)
        iam.create_policy(
            PolicyName=policy_name,
            Path='/',
            PolicyDocument=json.dumps(policy_doc),
            Description=('Allows the IAM user to which this policy '
                         'is attached to assume '
                         'the {role.name} role.'.format(role=role)))
    return pol


def ensure_group(iam,
                 group_name=DB_MIG_GROUP,
                 group_policies=DB_MIG_GROUP_POLICIES):
    """Group must have the IAMReadOnlyAccess policy attached."""
    group = iam.Group(group_name)
    try:
        group.load()
    except ClientError:
        logger.error(
            'AWS IAM Group {!r} does not exist.'.format(group_name))
        click.get_current_context().abort()

    users = list(group.users.all())
    if not users:
        raise Exception('No users added to the "{}" '
                        'AWS IAM group {}'.format(group_name))
    group_policy_names = set(group_policies)
    for policy in iam.policies.all():
        if policy.policy_name in group_policy_names:
            group.attach_policy(PolicyArn=policy.arn)
    return group


def attached_assume_role_policy(user, assume_role_policy_name):
    existing_policies = {pol.policy_name: pol
                         for pol in user.attached_policies.all()}
    return existing_policies.get(assume_role_policy_name)


def sync_user(iam, user, assume_role_policy_name, role_name=DB_MIG_ROLE):
    arp = attached_assume_role_policy(user, assume_role_policy_name)
    if arp is None:
        assume_role_policy = get_policy_by_name(iam, assume_role_policy_name)
        user.attach_policy(PolicyArn=assume_role_policy.arn)
    role = iam.Role(role_name)
    arpd = dict(role.assume_role_policy_document)
    users = arpd['Statement'][0]['Principal']['AWS']
    if user.arn not in users:
        users.append(user.arn)
        arp = role.AssumeRolePolicy()
        arp.update(PolicyDocument=json.dumps(arpd))


def ensure_user(iam, username,
                group_name=DB_MIG_GROUP,
                role_name=DB_MIG_ROLE):
    group = iam.Group(group_name)
    users = {user.name: user for user in group.users.all()}
    if username not in users:
        group.add_user(UserName=username)
    user = iam.User(username)
    sync_user(iam, user)
    return user


def sync_migration_users(iam, assume_role_policy_name,
                         role_name=DB_MIG_ROLE,
                         group_name=DB_MIG_GROUP):
    group = iam.Group(group_name)
    for user in group.users.all():
        sync_user(iam, user, assume_role_policy_name,
                  role_name=role_name)


def users(iam, assume_role_policy_name,
          role_name=DB_MIG_ROLE,
          group_name=DB_MIG_GROUP,
          verify=True):
    group = iam.Group(group_name)
    users = []
    role = iam.Role(role_name)
    role_arp_stmt = role.assume_role_policy_document['Statement'][0]
    trusted_user_arns = set(role_arp_stmt['Principal']['AWS'])
    arp = get_policy_by_name(iam, assume_role_policy_name)
    errors = []
    for user in sorted(group.users.all(), key=operator.attrgetter('name')):
        arp = attached_assume_role_policy(user, assume_role_policy_name)
        assume_role_policy_attached = arp is not None
        user_trusted_by_role = user.arn in trusted_user_arns
        assumes_role = assume_role_policy_attached and user_trusted_by_role
        if verify:
            if not assume_role_policy_attached:
                logger.error(
                    'User {} ({}) requires the trust-policy {}',
                    user.name,
                    user.arn,
                    get_policy_by_name(iam, assume_role_policy_name).arn)
                errors.append(assume_role_policy_attached)
                continue
            if not user_trusted_by_role:
                logger.error('User {} ({}) is not trusted by role {}',
                             user.name,
                             user.arn,
                             role.arn)
                errors.append(user_trusted_by_role)
                continue
        users.append(dict(name=user.name,
                          arn=user.arn,
                          assumes_role=assumes_role))
    user_data = dict(group=dict(name=group_name, users=users))
    return (user_data, errors)
