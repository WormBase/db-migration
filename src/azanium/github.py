import os

import github3


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