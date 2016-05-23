import contextlib
import io
import os
import subprocess

import paramiko


class RemoteCommandFailed(Exception):
    """Running the remote command failed."""


@contextlib.contextmanager
def connection(ec2_instance,
               timeout=30,
               username='ec2-user',
               private_key_path=None):
    hostname = ec2_instance.public_dns_name
    if private_key_path is None:
        # Use the instance private key
        private_key_path = os.path.join(os.getcwd(),
                                        ec2_instance.key_pair.name)
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname,
                key_filename=private_key_path,
                username=username,
                timeout=timeout)  
    yield ssh
    ssh.close()


def read_stream(stream, block_size=2048, encoding=None):
    if encoding is None:
        buf = io.BytesIO()
    else:
        buf = io.StringIO()
    while True:
        data = stream.read(block_size)
        if encoding is not None:
            data = data.decode('utf-8')
        buf.write(data)
    return buf.getvalue()


def run_command(ec2_instance, cmd, timeout=30):
    """Run a command over ssh."""
    with connection(ec2_instance) as ssh:
        (stdin, stdout, stderr) = ssh.exec_command(cmd)
        stdin.close()
        out = read_stream(stdout)
        err = read_stream(stderr)
        if err:
            raise RemoteCommandFailed(err)
    return out
