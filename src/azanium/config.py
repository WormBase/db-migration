import os

from configobj import ConfigObj

PATH = os.path.expanduser('~/.azanium.conf')


def parse(path=PATH):
    """Parse configuraion for this package.

    Keys in the configuration are in "dotted notation".
    e.g: azanium.config

    :param path: The path to the configuration file.
    :type path: str
    :rtype: dict
    :returns: The configuration for this package.
    """
    with open(path) as fp:
        conf = ConfigObj(infile=fp)
    return conf[__name__]
