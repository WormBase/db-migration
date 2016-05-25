import functools
import io
import os

import paramiko
from botocore.exceptions import ClientError


keypair_directory = functools.partial(os.path.expanduser, '~/.ssh')


class RemoteCommandFailed(Exception):
    """Running the remote command failed."""


def recycle_key_pair(ec2, key_pair_name):
    try:
        key_pair = ec2.KeyPair(key_pair_name)
        key_pair.load()
    except ClientError:
        # KeyPair not present in EC2
        pass
    else:
        key_pair.delete()
    key_pair = ec2.create_key_pair(KeyName=key_pair_name)
    key_filename = '{}.pem'.format(key_pair_name)
    key_pair_path = os.path.join(keypair_directory(), key_filename)
    try:
        os.remove(key_pair_path)
    except OSError:
        pass
    # If the user has deleted the keypair locally, re-create
    with open(key_pair_path, 'wb') as fp:
        fp.write(key_pair.key_material.encode('ascii'))
        os.chmod(fp.name, 0o600)
    return key_pair


def connection(ec2_instance, timeout=30, username='ec2-user'):
    hostname = ec2_instance.public_dns_name
    keypair_filename = ec2_instance.key_pair.name + '.pem'
    key_filename = os.path.join(keypair_directory(), keypair_filename)
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname,
                key_filename=key_filename,
                username=username,
                timeout=timeout)
    return ssh


def read_stream(stream, block_size=2048, encoding='utf-8'):
    while True:
        data = stream.read(block_size)
        if not data:
            break
        if encoding is not None:
            data = data.decode(encoding)
        yield data


def run_command(ec2_instance, cmd,
                ssh_conn=None, timeout=30, ignore_err=False):
    """Run a command over ssh."""
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    if ssh_conn is None:
        ssh_conn = connection(ec2_instance)
    with ssh_conn:
        (stdin, stdout, stderr) = ssh_conn.exec_command(cmd,
                                                        timeout=timeout,
                                                        get_pty=True)
        stdin.close()
        out = read_stream(stdout)
        err = read_stream(stderr)
        for block in err:
            err_buf.write(block)
        err_text = err_buf.getvalue()
        if err_text:
            print('Got error text: ' + err_text)
            raise RemoteCommandFailed(err_text)
        for block in out:
            out_buf.write(block)
    return out_buf
