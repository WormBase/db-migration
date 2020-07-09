import os
import shutil
import tarfile
import tempfile
import urllib.parse
import zipfile


import click

from . import artefact
from . import config
from . import github
from . import log
from . import notifications
from . import root_command
from . import util

logger = log.get_logger(__name__)


def abort(msg):
    util.echo_error(msg)
    raise click.Abort(msg)


def preliminary_checks():
    # check github release of wb pipeline is done
    # check that the az configuration file is present
    # warn if slack notifications are not to be sent (not configured)
    conf = config.parse()
    if not conf:
        abort( ' '.join([__package__,
                         ' has not been configured, run: '
                         '"azanium configure" to fix this']))
    ws_release_version = util.get_data_release_version()
    if not ws_release_version:
        abort('azanium configure has not been run')
    if not conf['sources'].as_bool('is_released'):
        abort('The wormbase-pipeline repo has not been tagged on github')
    if notifications.__name__ not in conf:
        warning_msgs = [
            'Slack notifications are not enabled - integration has been disabled',
            'It is safe to re-run the "azanium configure" command '
            'after the current command exits, should you wish to '
            'enable notifications']
        for warning_msg in warning_msgs:
            logger.warn(warning_msgs)
            util.warn(warning_msgs)


@root_command.group(chain=True, invoke_without_command=True)
@util.pass_command_context
def installers(ctx):
    """Software installers for the WormBase database migration.

    All software will be installed under a common base path,
    as specified to the parent command.
    """

@installers.resultcallback()
def pipeline(installers, *args, **kw):
    for install_command in filter(callable, installers):
        install_command(*args, **kw)


@installers.command(short_help='Installs the ACeDB "tace" binary')
@util.option('-t', '--url-template',
             default=('ftp://ftp.sanger.ac.uk/pub/acedb/MONTHLY/'
                      'ACEDB-binaryLINUX_{version}.tar.gz'),
             help='URL for versioned ACeDB binaries')
@artefact.prepared
def tace(context, afct, url_template=None):
    """Installs the ACeDB "tace" binary program."""
    version = afct.version
    url = url_template.format(version=version)
    pr = urllib.parse.urlparse(url)
    downloaded = util.ftp_download(pr.netloc,
                                   os.path.basename(pr.path),
                                   afct.download_dir,
                                   logger,
                                   initial_cwd=os.path.dirname(pr.path))
    local_path = downloaded[0]
    with tarfile.open(local_path) as tf:
        tf.extract('./tace', path=afct.install_dir)
    tace_path = os.path.join(afct.install_dir, 'tace')
    util.touch_dir(afct.install_dir)
    util.make_executable(tace_path, logger)
    return tace_path


@installers.command(short_help='Installs datomic-free')
@util.option('-t', '--url-template',
             default='https://my.datomic.com/downloads/free/{version}',
             help='URL template for Datomic Free version')
@artefact.prepared
def datomic_free(context, afct, url_template=None):
    """Installs Datomic (free version)."""
    install_dir = afct.install_dir
    version = afct.version
    url = url_template.format(version=version)
    fullname = 'datomic-free-{version}'.format(version=version)
    local_filename = fullname + '.zip'
    download_path = os.path.join(afct.download_dir, local_filename)
    logger.info('Downloading and extracting {} to {}', fullname, install_dir)
    tmpdir = tempfile.mkdtemp()
    with zipfile.ZipFile(util.download(url, download_path)) as zf:
        zf.extractall(tmpdir)
    shutil.rmtree(install_dir)
    shutil.move(os.path.join(tmpdir, fullname), install_dir)
    util.touch_dir(install_dir)
    logger.info('Installed {} into {}', fullname, install_dir)
    logger.info('Setting environment variable DATOMIC_HOME={}', install_dir)
    bin_dir = os.path.join(install_dir, 'bin')
    for filename in os.listdir(bin_dir):
        bin_path = os.path.join(bin_dir, filename)
        util.make_executable(bin_path, logger, symlink_dir=None)
    os.chdir(install_dir)
    mvn_install = os.path.join('bin', 'maven-install')
    logger.info('Installing datomic via {}', os.path.abspath(mvn_install))
    mvn_install_out = util.local(mvn_install)
    logger.info('Installed datomic_free')
    logger.debug(mvn_install_out)
    return install_dir


@installers.command(short_help='Installs pseudoace')
@artefact.prepared
def pseudoace(context, afct, **kw):
    """Installs pseudoace."""
    download_dir = afct.download_dir
    install_dir = afct.install_dir
    tag = afct.version
    logger.info('Downloading pseudoace release {} from github', tag)
    dl_path = github.download_release_binary(
        'WormBase/pseudoace',
        tag,
        to_directory=download_dir)
    tempdir = tempfile.mkdtemp()
    with tarfile.open(dl_path) as tf:
        tf.extractall(path=tempdir)
    archive_filename = os.path.split(dl_path)[-1]
    fullname = archive_filename.rsplit('.', 2)[0]
    tmp_src_path = os.path.join(tempdir, fullname)
    src_path = tmp_src_path.rstrip('-' + tag)
    os.rename(tmp_src_path, src_path)
    shutil.rmtree(install_dir)
    shutil.move(src_path, install_dir)
    util.touch_dir(install_dir)
    logger.info('Extracted {} to {}', archive_filename, install_dir)
    return install_dir


@root_command.command('install', short_help='Installs everything')
@util.pass_command_context
def install(context):
    """Installs all software and data."""
    # Invoke all commands via the install group command chain.
    # This has the same effect as if run on command line, e.g:
    # azanium install dataomic_free pseudoace acedb_database ..
    preliminary_checks()
    ctx = click.get_current_context()
    install_cmd_names = sorted(installers.commands)
    orig_protected_args = ctx.protected_args[:]
    ctx.protected_args.extend(install_cmd_names)
    try:
        installers.invoke(ctx)
    finally:
        ctx.protected_args[:] = orig_protected_args
    attachments = []
    versions = util.get_deploy_versions()
    for name in install_cmd_names:
        version = versions[name]
        title = 'Installed {} (version: {})'.format(name, version)
        ts = os.path.getmtime(context.path(name))
        attachment = notifications.Attachment(title, ts=ts)
        attachments.append(attachment)
    return attachments
