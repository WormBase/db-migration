import os
import platform
import re
import urllib.parse

import click
import requests


class URL(click.types.ParamType):

    name = 'url'
    human_readable_name = 'URL'
    opts = None

    def __init__(self, human_readable_name=None, **pr_match_kw):
        """Initializes a click option type.

        :params human_readable_name: Name shown to user.

        Names of keywords provided as ``pr_match_kw`` (if any)
        should match the attributes of ``urllib.parse.ParseResult`` -
        the return type of ``urllib.parse.urlparse ``.
        """
        if human_readable_name is not None:
            self.human_readable_name = human_readable_name
        self.match_parse_result = pr_match_kw

    def convert(self, value, param, ctx):
        """Ensures `value` is a valid Slack webhook url."""
        try:
            pr = urllib.parse.urlparse(value)
            for (k, v) in self.match_parse_result.items():
                fail = re.match(v, getattr(pr, k)) is None
                if fail:
                    break
            else:
                fail = False
        except AttributeError:
            fail = True
        else:
            response = requests.get(pr.geturl())
            if response.status_code != 400:
                self.fail('Invalid {.human_readable_name}'.format(self))
        if fail:
            msg = '{0!r} is not a valid {1.human_readable_name}'
            self.fail(msg.format(value, self), param, ctx)
        return value


def smart_dir(path):
    """Construct a click Path paramter type, dependant upon platform."""
    path_param = click.types.Path(file_ok=False, writeable=True)
    return path_param


class PlatformAwareDirectory(click.types.ParamType):

    name = 'platform-aware-directory'

    # this is a string that should appear to identify the machine
    # as an Amazon based AMI
    aws_platform_marker = 'amzn'

    def __init__(self):
        self._param = click.types.Path(exists=self.is_aws_machine(),
                                       file_okay=False,
                                       dir_okay=True,
                                       allow_dash=True,
                                       readable=True,
                                       writable=True)

    def is_aws_machine(self):
        return self.aws_platform_marker in platform.platform()

    def convert(self, value, param, ctx):
        try:
            os.stat(value)
        except OSError:
            if not self._param.exists and value.startswith('/'):
                value = os.path.join(os.path.expanduser('~'),
                                     os.path.basename(value))
        path = self._param.convert(value, param, ctx)
        return path
