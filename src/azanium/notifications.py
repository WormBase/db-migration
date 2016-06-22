import collections
import importlib
import os
import time
import threading

import requests

from . import log
from . import params

DEFAULTS = dict(icon_emoji=':wormbase-db-dev:')

SLACK_HOOK_URL = params.URL(human_readable_name='Slack webhook URL',
                            scheme='https',
                            netloc='hooks.slack.com',
                            path='/services/\w+/\w+/\w+')

def _notify_noop(*args, **kw):
    logger = log.get_logger(__name__)
    logger.warn('Notifications are not going to sent - '
                'azanium not configured with slack URL')

def _notify(conf,
            message,
            attachments=None,
            icon_emoji=None,
            channel=None,
            username=None,
            color=None,
            n_retries=3):
    log = importlib.import_module(__package__ + '.log')
    logger = log.get_logger(namespace=__name__)
    data = dict(text=message)

    # XXX: remove - debugging!
    channel = 'test-webhook-for-mig'
    if attachments is not None:
        if isinstance(attachments, Attachment):
            attachments = [attachments]
        elif isinstance(attachments, str):
            attachments = [Attachment(title=attachments)]
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


def notify(config, *args, **kw):
    delegate = _notify if config else _notify_noop
    return delegate(config, *args, **kw)


def notify_threaded(*args, **kw):
    t = threading.Thread(target=notify, args=args, kwargs=kw)
    t.start()
    t.join()


def around(func, config, headline, message, pre_kw=None, post_kw=None):
    pre_kw = pre_kw if pre_kw else {}
    post_kw = post_kw if post_kw else {}
    post_kw.setdefault('color', 'good')
    attachments_pre = [Attachment(title=message)]
    notify(config, headline, attachments=attachments_pre, **pre_kw)
    result = func()
    notify(headline + ' - *complete*', attachments=result, **post_kw)


class Attachment(collections.Mapping):

    def __init__(self, title, **kw):
        self.title = title
        self.fields = []
        self.data = dict(title=self.title,
                         fallback=kw.get('fallack', 'Fallback:' + self.title),
                         pretext=kw.get('pretext', ''),
                         mrkdwn_in=['fields', 'pretext', 'text'],
                         color=kw.get('color', 'good'),
                         ts=kw.get('ts', time.time()),
                         fields=self.fields)

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
        field = {}
        field['value'] = value
        field['short'] = len(value) <= 120
        self.fields.append(field)

    def add_file(self, file_like):
        if isinstance(file_like, str) and os.path.isfile(file_like):
            file_like = open(file_like, 'rb')
        with file_like as fp:
            self.add_content(fp.read())
