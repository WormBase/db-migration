import base64
import contextlib
import os

import git
import github3


from . import config


def _prompt(question):
    answer = ''
    while not answer:
        answer = input(question + ': ').strip()
    return answer


@contextlib.contextmanager
def login(scopes=('user', 'repo')):
    conf = config.parse()
    saved_auth = conf.get(__name__, {})
    if not saved_auth:
        username = _prompt('GitHub username')
        password = _prompt('GitHub password')
        uniq = base64.b64encode(os.urandom(16))[:-2].decode('ascii')
        note = __package__ + ' session ' + uniq
        auth =  github3.authorize(username, password, scopes, note=note)
        saved_auth = {'auth.token': auth.token, 'auth.id': auth.id}
        conf[__name__] = saved_auth
        config.write(conf)
    token = saved_auth['auth.token']
    gh = github3.login(token=token)
    yield gh


def repo_from_path(repo_path):
    (org_name, _, repo_name) = repo_path.partition('/')
    return github3.repository(org_name, repo_name)


def download_release_binary(repo_path, tag, to_directory=None):
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
    repo = repo_from_path(repo_path)
    release = repo.release_from_tag(tag)
    asset = next(release.assets(), None)
    asset_tarball_name = '{name}-{version}.tar.gz'.format(name=repo.name,
                                                          version=tag)
    if asset is None or asset.name != asset_tarball_name:
        msg = 'Expected asset {!r} has not been uploaded to github releases'
        raise EnvironmentError(msg.format(asset_tarball_name))
    local_path = os.path.join(to_directory, asset.name)
    return asset.download(path=local_path)


def infer_from_local_repo(path=None, gh=github3):
    path = path if path else os.getcwd()
    git_url = git.Repo(path).remotes.origin.url
    (org, repo_name) = git_url.rsplit(':')[1].rsplit('.')[0].split('/')
    return gh.repository(org, repo_name)


def publish_release(reporoot, version, bundle_path):
    """A zest.releaser hook for publishing releases to github."""
    with login() as gh:
        repo = infer_from_local_repo(path=reporoot, gh=gh)
    release = repo.release_from_tag(version)
    if release.is_null():
        release = repo.create_release(version)
    with open(bundle_path, 'rb') as fp:
        filename = os.path.basename(fp.name)
        asset = release.upload_asset('application/zip', filename, fp)
    return asset

def read_released_file(repo_root, release_tag, path):
    tags = (t.as_dict() for t in repo_root.tags())
    named_tags = {tag['name']: tag for tag in tags}
    tag = named_tags[release_tag]
    if repo_root.release_from_tag(release_tag).is_null():
        raise RuntimeError('checkout of file from a non-release tag forbidden')
    file_contents = repo_root.file_contents(path, tag['commit']['sha'])
    return file_contents.decoded

    
