import os
import glob

from . import github
from . import log
from . import util


log = log.get_logger(__name__)


def build_release_assets(release_data):
    """Build the assets for a github release and the docs for github-pages.

    ``release_data`` is a dictionary of the release data as passed by
    ```zest.releaser`.

    :param release_data: A mapping passed by the `zest.releaser` tool.
    :type release_data: dict
    """
    #Build python wheel distribution package
    util.setup_py('bdist_wheel -d dist/')

    #Build docs
    util.local('make docs')

    log.info('Created assets for new release {}', release_data['version'])

def deploy_release(release_data):
    """Deploy code to a github release, docs to github-pages.

    ``release_data`` is a dictionary of the release data as passed by
    ```zest.releaser`.

    :param release_data: A mapping passed by the `zest.releaser` tool.
    :type release_data: dict
    """
    #Push code and release tag to github
    github.push_remote(release_data['reporoot'])
    #Deploy GH release
    bundle_path = glob.glob('dist/azanium-'+release_data['version']+'-*.whl')[0]
    asset = github.publish_release(release_data['reporoot'],
                                   release_data['version'],
                                   bundle_path)
    util.local('make deploy-docs')
    log.info('Uploaded {} to new release {}',
             asset.browser_download_url,
             release_data['version'])
