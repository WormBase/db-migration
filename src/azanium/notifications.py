import collections
import os
import re
import urllib
import threading

from configobj import ConfigObj
import click
import requests

from . import log

CONF_PATH = os.path.expanduser('~/.azanium.conf')

DEFAULTS = dict(channel='wb-db-migration-alerts',
                icon_emoji=':wormbase-db-dev:')


class URL(click.types.ParamType):

    name = 'url'
    human_readable_name = 'URL'
    opts = None

    def __init__(self, human_readable_name=None, **pr_match_kw):
        if human_readable_name is not None:
            self.human_readable_name = human_readable_name
        self.match_parse_result = pr_match_kw

    def convert(self, value, param, ctx):
        try:
            pr = urllib.parse.urlparse(value)
            for (k, v) in self.match_parse_result.items():
                fail = re.match(v, getattr(pr, k)) is None
                if fail:
                    break
            else:
                fail = False
        except Exception as e:
            fail = True
            raise e
        else:
            response = requests.get(pr.geturl())
            if response.status_code != 400:
                self.fail('Invalid {.human_readable_name}'.format(value))
        if fail:
            msg = '{0!r} is not a valid {1.human_readable_name}'
            self.fail(msg.format(value, self), param, ctx)
        return value


SLACK_HOOK_URL = URL(human_readable_name='Slack webhook URL',
                     scheme='https',
                     netloc='hooks.slack.com',
                     path='/services/\w+/\w+/\w+')


def notify(message,
           attachments=None,
           icon_emoji=None,
           channel=None,
           username=None,
           color=None,
           n_retries=3):
    conf = config.parse()
    log = importlib.import_module(__package__ + '.log')
    logger = log.get_logger(namespace=__name__)
    data = dict(text=message)

    # XXX: remove - debugging!
    channel = 'test-webhook-for-mig'
    if attachments is not None:
        if isinstance(attachments, Attachment):
            attachments = [attachments]
        data['attachments'] = list(map(dict, attachments))
    if channel is not None:
        if not channel.startswith('#'):
            channel = '#' + channel
        data['channel'] = channel
    if icon_emoji is not None:
        data['icon_emoji'] = icon_emoji
    if username is not None:
        data['username'] = username
    if color is not None:
        data['color'] = color
    for attempt_n in range(1, n_retries + 1):
        with requests.Session() as request:
            response = request.post(conf['url'], json=data)
            if 200 >= response.status_code <= 302:
                logger.debug('sent notification {} to {}',
                             repr(data),
                             conf['url'])
                break
            logger.warn('Failed to send notification (attempt {:d})',
                        attempt_n)
    else:
        logger.error('Failed to send notification')
        logger.info('Notificaiton data: {}', repr(data))


def notify_threaded(*args, **kw):
    kw.setdefault('channel', 'test-webhook-for-mig')
    t = threading.Thread(target=notify, args=args, kwargs=kw)
    t.start()
    t.join()


class Attachment(collections.Mapping):

    def __init__(self, title, **kw):
        self._fields = dict(title=title, value='', short=False)
        self.data = dict(fallback=kw.get('fallack', title),
                         pretext=kw.get('pretext', ''),
                         fields=self._fields)

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, name):
        return self.data[name]

    def add_content(self, content):
        if isinstance(content, str):
            value = content
        elif isinstance(content, bytes):
            value = content.decode('utf-8')
        else:
            raise ValueError('content must be str or bytes')
        self._fields['value'] = value
        self._fields['sort'] = len(value) <= 120

    def add_file(self, file_like):
        if isinstance(file_like, str) and os.path.isfile(file_like):
            file_like = open(file_like, 'rb')
        with file_like as fp:
            self.add_content(fp.read())
