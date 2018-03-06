import functools
import importlib
import logging
import os
import traceback

from . import util


class Message:

    def __init__(self, fmt, args):
        self.fmt = fmt
        self.args = args

    def __str__(self):
        return self.fmt.format(*self.args)


class Logger(logging.LoggerAdapter):

    def __init__(self, logger, extra=None):
        super(Logger, self).__init__(logger, extra or {})

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            self.exception(str(exc_value))
            raise exc_value

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

    def __init__(self, *args, **kw):
        self._notify = kw.pop('notify', False)
        Logger.__init__(self, *args, **kw)

    def exception(self, msg, *args, **kw):
        if self._notify:
            # avoid circular import
            notifications = importlib.import_module(__package__ +
                                                    '.notifications')
            att = notifications.Attachment(
                str(msg),
                preface='An unexpected error occurred')
            att.add_content(traceback.format_exc())
            notifications.notify_threaded(
                '*Looks like we have a bug here...*',
                attachments=[att],
                color='danger',
                icon_emoji=':bug:')
        return super(VerbosePrettyLogger, self).exception(msg, *args, **kw)


def setup_logging(logfile_path, log_level=logging.INFO):
    log_dir = os.path.dirname(logfile_path)
    log_filename = os.path.basename(logfile_path)
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_filename)
    logging.basicConfig(filename=log_path,
                        format='{asctime:12s} {levelname:5s} {name} {message}',
                        style='{',
                        level=log_level)
    root_logger = get_logger(__package__)
    root_logger.setLevel(log_level)
    root_logger.debug('Logging to {} at level {}',
                      log_path,
                      logging.getLevelName(root_logger.logger.level))


def get_logger(namespace=None, verbose=True, notify=True):
    adapter = VerbosePrettyLogger if verbose else Logger
    return adapter(logging.getLogger(namespace), notify=notify)
