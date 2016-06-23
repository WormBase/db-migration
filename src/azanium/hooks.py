import os
import tempfile

from . import github
from . import log
from . import util


log = log.get_logger(__name__)


def deploy_release(release_data):
    """Deploy code to a github release, docs to github-pages.

    ``release_data`` is a dictionary of the release data as passed by
    ```zest.releaser`.

    :param release_data: A mapping passed by the `zest.releaser` tool.
    :type release_data: dict
    """
    tempdir = tempfile.mkdtemp()
    util.setup_py('bdist_wheel -d ' + tempdir)
    bundle_path = os.path.join(tempdir, os.listdir(tempdir)[0])
    asset = github.publish_release(release_data['reporoot'],
                                   release_data['version'],
                                   bundle_path)
    util.local('make deploy-docs')
    log.info('Uploaded {} to new release {}',
             asset.browser_download_url,
             release_data['version'])
