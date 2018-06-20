import logging
import os

from configobj import ConfigObj


PATH = os.path.expanduser('~/.azanium.conf')


def parse(path=PATH, section=None):
    """Parse configuraion for this package.

    Keys in the configuration are in "dotted notation".
    e.g: `azanium.config`

    :param path: The path to the configuration file.
    :type path: str
    :rtype: dict
    :returns: The configuration for this package.
    """
    try:
        with open(path) as fp:
            conf = ConfigObj(infile=fp)
    except FileNotFoundError:
        conf = {}
    return conf[section] if section is not None else conf


def write(config):
    with open(PATH, 'wb') as fp:
        config.write(fp)
