import os
import github3

from .util import download


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
    (org_name, _, repo_name) = repo_path.partition('/')
    repo = github3.repository(org_name, repo_name)
    release = repo.release_from_tag(tag)
    markdown_text = release.body
    li = markdown_text.find('(') + 1
    ri = markdown_text.rfind(')')
    download_url = markdown_text[li:ri]
    if to_directory is None:
        to_directory = os.getcwd()
    local_filename = download_url.rsplit('/')[-1]
    local_path = os.path.join(to_directory, local_filename)
    return download(download_url, local_path)
