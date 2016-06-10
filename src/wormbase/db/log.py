import functools
import logging
import os
import sys

from . import util


class Message(object):

    def __init__(self, fmt, args):
        self.fmt = fmt
        self.args = args

    def __str__(self):
        return self.fmt.format(*self.args)


class Logger(logging.LoggerAdapter):

    def __init__(self, logger, extra=None):
        super(Logger, self).__init__(logger, extra or {})

    def log(self, level, msg, *args, **kw):
        if self.isEnabledFor(level):
            msg, kw = self.process(msg, kw)
            self.logger._log(level, Message(msg, args), (), **kw)


class VerboseLogMethod:

    def __init__(self, name, printer=print):
        self._name = name
        self._printer = printer

    def __get__(self, obj, objtype=None):
        method = getattr(super(objtype, obj), self._name)

        def logprint_dispatch(method, msg, *args, **kw):
            level = getattr(logging, self._name.upper())
            if obj.logger.isEnabledFor(level):
                self._printer(msg.format(*args, **kw))
            return method(msg, *args, **kw)

        return functools.partial(logprint_dispatch, method)


class VerbosePrettyLogger(Logger):

    debug = VerboseLogMethod('debug')
    error = VerboseLogMethod('error', util.echo_error)
    info = VerboseLogMethod('info', util.echo_info)
    warning = VerboseLogMethod('warning', util.echo_warning)


def setup_logging(log_filename=None, log_level=logging.INFO):
    if log_filename is None:
        log_filename = os.path.basename(sys.argv[0]) + '.log'
    log_dir = util.install_path('logs')
    log_path = os.path.join(log_dir, log_filename)
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(filename=log_path,
                        format='{asctime:12s} {levelname:5s} {name} {message}',
                        style='{',
                        level=log_level)
    root_logger = get_logger(__package__)
    root_logger.setLevel(log_level)
    root_logger.debug('Logging to {} at level {}',
                      log_path,
                      logging.getLevelName(root_logger.logger.level))


def get_logger(namespace=None, verbose=True):
    adapter = VerbosePrettyLogger if verbose else Logger
    return adapter(logging.getLogger(namespace))
