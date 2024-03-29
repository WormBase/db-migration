import base64
import contextlib
import os
import sys

import git
import github3
import getpass

import urllib.parse
import re

from . import config


WB_PIPELINE_REPO = 'WormBase/wormbase-pipeline'


def _prompt(question):
    answer = ''
    while not answer:
        answer = input(question + ': ').strip()
    return answer


@contextlib.contextmanager
def login(reporoot, force_prompt=False):
    conf = config.parse()
    saved_auth = conf.get(__name__, {})
    gh = None

    while True:
        if force_prompt or not saved_auth or not saved_auth['auth.pers-token']:
            username = _prompt('GitHub username')
            token = getpass.getpass(prompt='GitHub personal access token: ')
            saved_auth = {'auth.username': username, 'auth.pers-token': token}
            conf[__name__] = saved_auth
            config.write(conf)
        username = saved_auth['auth.username']
        token = saved_auth['auth.pers-token']
        gh = github3.login(username = username, token=token)

        (org, repo_name) = parse_local_remote(path=reporoot)

        try:
            gh.repository(org, repo_name)
            break
        except github3.exceptions.AuthenticationFailed:
            print('WARNING: Github Authentication Failed. Provide a valid username and personal token to try again.')
            force_prompt = True

    yield gh


def repo_from_path(repo_path, gh=github3):
    (org_name, _, repo_name) = repo_path.partition('/')
    return gh.repository(org_name, repo_name)


def download_release_binary(repo_path, tag, to_directory=None, gh=github3):
    """Download a release binary from `repo_path` to `to_directory`.

    `to_directory` will be the current working direcnutory by default.

    Assumes that a binary release has been attached to a release.

    :param repo_path: The path to the github repo.
    :type repo_path: str
    :param tag: The git tag for the release.
    :type tag: str
    :param to_directory: The directory to save the binary into.
    :type to_directory: str
    :returns: The path to the saved file.
    :rtype: str
    """
    repo = repo_from_path(repo_path, gh=gh)
    release = repo.release_from_tag(tag)
    asset = next(release.assets(), None)
    asset_tarball_name = '{name}-{version}.tar.xz'.format(name=repo.name,
                                                          version=tag)
    if asset is None or asset.name != asset_tarball_name:
        msg = 'Expected asset {!r} has not been uploaded to github releases'
        raise EnvironmentError(msg.format(asset_tarball_name))
    local_path = os.path.join(to_directory, asset.name)
    return asset.download(path=local_path)


def parse_local_remote(path=None):
    path = path if path else os.getcwd()
    git_url = git.Repo(path).remotes.origin.url
    (org, repo_name) = re.split(r'[:/]', urllib.parse.urlparse(git_url).path.split('.')[-2])[1:]
    return (org, repo_name)

def get_gh_repo_from_local_remote(path=None, gh=github3):
    (org, repo_name) = parse_local_remote(path=path)
    return gh.repository(org, repo_name)


def push_remote(reporoot):
    """A function for pushing local changes to github, independent from zest.releaser.
       Used by a zest.releaser hook to push code after release tagging but before \
       GH release creation and new development commits."""

    response = str(input("Azanium: OK to push local changes to remote (Y/n)? ") or "y").lower()

    if response == 'y':
        repo = git.Repo(reporoot)
        origin = repo.remotes.origin
        origin.push()
    else:
        print("Interrupting on user request...")
        sys.exit(1)


def publish_release(reporoot, version, bundle_path):
    """A function for publishing releases to github, used by a zest.releaser hook."""
    with login(reporoot) as gh:
        repo = get_gh_repo_from_local_remote(path=reporoot, gh=gh)
        try:
            release = repo.release_from_tag(version)
        except github3.exceptions.NotFoundError:
            print('WARNING: Release not found on GitHub. Creating new release.')
            release = repo.create_release(version)
        with open(bundle_path, 'rb') as fp:
            filename = os.path.basename(fp.name)
            asset = release.upload_asset('application/zip', filename, fp)
    return asset


def is_released(ws_version):
    repo = repo_from_path(WB_PIPELINE_REPO)
    return bool(repo.release_from_tag(ws_version))


def read_released_file(repo, data_version, path):
    tags = (t.as_dict() for t in repo.tags())
    named_tags = {tag['name']: tag for tag in tags}
    release = repo.release_from_tag(data_version)
    if not release:
        raise RuntimeError('No release tag for data version: ' + data_version)
    tag = named_tags[release.tag_name]
    file_contents = repo.file_contents(path, tag['commit']['sha'])
    return file_contents.decoded

