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


def read_stream(stream, block_size=2048, encoding='utf-8'):
    while True:
        data = stream.read(block_size)
        if not data:
            break
        if encoding is not None:
            data = data.decode(encoding)
        yield data


def run_command(ec2_instance, cmd, timeout=30):
    """Run a command over ssh."""
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with connection(ec2_instance) as ssh:
        (stdin, stdout, stderr) = ssh.exec_command(cmd)
        stdin.close()
        out = read_stream(stdout)
        err = read_stream(stderr)
        if err:
            for block in err:
                err_buf.write(block)
            raise RemoteCommandFailed(err_buf.getvalue())
        for block in out:
            out_buf.write(block)
    return out_buf
