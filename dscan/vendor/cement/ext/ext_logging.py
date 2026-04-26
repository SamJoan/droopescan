"""Logging Framework Extension"""

import os
import logging
from ..core import exc, log, handler
from ..utils.misc import is_true, minimal_logger
from ..utils import fs

LOG = minimal_logger(__name__)

try:                                        # pragma: no cover
    NullHandler = logging.NullHandler       # pragma: no cover
except AttributeError as e:                 # pragma: no cover
    # Not supported on Python < 3.1/2.7     # pragma: no cover
    class NullHandler(logging.Handler):     # pragma: no cover

        def handle(self, record):           # pragma: no cover
            pass                            # pragma: no cover
            # pragma: no cover

        def emit(self, record):             # pragma: no cover
            pass                            # pragma: no cover
            # pragma: no cover

        def createLock(self):               # pragma: no cover
            self.lock = None                # pragma: no cover


class LoggingLogHandler(log.CementLogHandler):

    """
    This class is an implementation of the :ref:`ILog <cement.core.log>`
    interface, and sets up the logging facility using the standard Python
    `logging <http://docs.python.org/library/logging.html>`_ module.

    Configuration Options

    The following configuration options are recognized in this class
    (assuming that Meta.config_section is `log.logging`):

        * level
        * file
        * to_console
        * rotate
        * max_bytes
        * max_files


    A sample config section (in any config file) might look like:

    .. code-block:: text

        [log.logging]
        file = /path/to/config/file
        level = info
        to_console = true
        rotate = true
        max_bytes = 512000
        max_files = 4

    """

    #: Handler meta-data.
    class Meta:
        #: The interface that this class implements.
        interface = log.ILog

        #: The string identifier of this handler.
        label = 'logging'

        #: The logging namespace.
        #:
        #: Note: Although Meta.namespace defaults to None, Cement will set
        #: this to the application label (CementApp.Meta.label) if not set
        #: during setup.
        namespace = None

        #: Class to use as the formatter
        formatter_class = logging.Formatter

        #: The logging format for the file logger.
        file_format = "%(asctime)s (%(levelname)s) %(namespace)s : " + \
                      "%(message)s"

        #: The logging format for the consoler logger.
        console_format = "%(levelname)s: %(message)s"

        #: The logging format for both file and console if ``debug==True``.
        debug_format = "%(asctime)s (%(levelname)s) %(namespace)s : " + \
                       "%(message)s"

        #: List of logger namespaces to clear.  Useful when imported software
        #: also sets up logging and you end up with duplicate log entries.
        #:
        #: Changes in Cement 2.1.3.  Previous versions only supported
        #: `clear_loggers` as a boolean, but did fully support clearing
        #: non-app logging namespaces.
        clear_loggers = []

        #: The default configuration dictionary to populate the ``log``
        #: section.
        config_defaults = dict(
            file=None,
            level='INFO',
            to_console=True,
            rotate=False,
            max_bytes=512000,
            max_files=4,
        )

    levels = ['INFO', 'WARN', 'ERROR', 'DEBUG', 'FATAL']

    def __init__(self, *args, **kw):
        super(LoggingLogHandler, self).__init__(*args, **kw)
        self.app = None

    def _setup(self, app_obj):
        super(LoggingLogHandler, self)._setup(app_obj)
        if self._meta.namespace is None:
            self._meta.namespace = "%s" % self.app._meta.label

        self.backend = logging.getLogger("cement:app:%s" %
                                         self._meta.namespace)

        # hack for application debugging
        if is_true(self.app._meta.debug):
            self.app.config.set(self._meta.config_section, 'level', 'DEBUG')

        level = self.app.config.get(self._meta.config_section, 'level')
        self.set_level(level)

        LOG.debug("logging initialized for '%s' using %s" %
                  (self._meta.namespace, self.__class__.__name__))

    def set_level(self, level):
        """
        Set the log level.  Must be one of the log levels configured in
        self.levels which are ``['INFO', 'WARN', 'ERROR', 'DEBUG', 'FATAL']``.

        :param level: The log level to set.

        """
        self.clear_loggers(self._meta.namespace)
        for namespace in self._meta.clear_loggers:
            self.clear_loggers(namespace)

        level = level.upper()
        if level not in self.levels:
            level = 'INFO'
        level = getattr(logging, level.upper())

        self.backend.setLevel(level)

        # console
        self._setup_console_log()

        # file
        self._setup_file_log()

    def get_level(self):
        """Returns the current log level."""
        return logging.getLevelName(self.backend.level)

    def clear_loggers(self, namespace):
        """Clear any previously configured loggers for `namespace`."""

        for i in logging.getLogger("cement:app:%s" % namespace).handlers:
            logging.getLogger("cement:app:%s" % namespace).removeHandler(i)
            self.backend = logging.getLogger("cement:app:%s" % namespace)

    def _get_console_format(self):
        if self.get_level() == logging.getLevelName(logging.DEBUG):
            format = self._meta.debug_format
        else:
            format = self._meta.console_format

        return format

    def _get_file_format(self):
        if self.get_level() == logging.getLevelName(logging.DEBUG):
            format = self._meta.debug_format
        else:
            format = self._meta.file_format

        return format

    def _get_file_formatter(self, format):
        return self._meta.formatter_class(format)

    def _get_console_formatter(self, format):
        return self._meta.formatter_class(format)

    def _setup_console_log(self):
        """Add a console log handler."""
        to_console = self.app.config.get(self._meta.config_section,
                                         'to_console')
        if is_true(to_console):
            console_handler = logging.StreamHandler()
            format = self._get_console_format()
            formatter = self._get_console_formatter(format)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(getattr(logging, self.get_level()))
        else:
            console_handler = NullHandler()

        self.backend.addHandler(console_handler)

    def _setup_file_log(self):
        """Add a file log handler."""

        file_path = self.app.config.get(self._meta.config_section, 'file')
        rotate = self.app.config.get(self._meta.config_section, 'rotate')
        max_bytes = self.app.config.get(self._meta.config_section,
                                        'max_bytes')
        max_files = self.app.config.get(self._meta.config_section,
                                        'max_files')
        if file_path:
            file_path = fs.abspath(file_path)
            log_dir = os.path.dirname(file_path)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            if rotate:
                from logging.handlers import RotatingFileHandler
                file_handler = RotatingFileHandler(
                    file_path,
                    maxBytes=int(max_bytes),
                    backupCount=int(max_files),
                )
            else:
                from logging import FileHandler
                file_handler = FileHandler(file_path)

            format = self._get_file_format()
            formatter = self._get_file_formatter(format)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(getattr(logging, self.get_level()))
        else:
            file_handler = NullHandler()

        self.backend.addHandler(file_handler)

    def _get_logging_kwargs(self, namespace, **kw):
        if namespace is None:
            namespace = self._meta.namespace

        if 'extra' in kw.keys() and 'namespace' in kw['extra'].keys():
            pass
        elif 'extra' in kw.keys() and 'namespace' not in kw['extra'].keys():
            kw['extra']['namespace'] = namespace
        else:
            kw['extra'] = dict(namespace=namespace)

        return kw

    def info(self, msg, namespace=None, **kw):
        """
        Log to the INFO facility.

        :param msg: The message the log.
        :param namespace: A log prefix, generally the module ``__name__`` that
            the log is coming from.  Will default to self._meta.namespace if
            None is passed.
        :keyword kw: Keyword arguments are passed on to the backend logging
            system.

        """
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.info(msg, **kwargs)

    def warn(self, msg, namespace=None, **kw):
        """
        Log to the WARN facility.

        :param msg: The message the log.
        :param namespace: A log prefix, generally the module ``__name__`` that
            the log is coming from.  Will default to self._meta.namespace if
            None is passed.
        :keyword kw: Keyword arguments are passed on to the backend logging
            system.

        """
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.warn(msg, **kwargs)

    def error(self, msg, namespace=None, **kw):
        """
        Log to the ERROR facility.

        :param msg: The message the log.
        :param namespace: A log prefix, generally the module ``__name__`` that
            the log is coming from.  Will default to self._meta.namespace if
            None is passed.
        :keyword kw: Keyword arguments are passed on to the backend logging
            system.

        """
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.error(msg, **kwargs)

    def fatal(self, msg, namespace=None, **kw):
        """
        Log to the FATAL (aka CRITICAL) facility.

        :param msg: The message the log.
        :param namespace: A log prefix, generally the module ``__name__`` that
            the log is coming from.  Will default to self._meta.namespace if
            None is passed.
        :keyword kw: Keyword arguments are passed on to the backend logging
            system.

        """
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.fatal(msg, **kwargs)

    def debug(self, msg, namespace=None, **kw):
        """
        Log to the DEBUG facility.

        :param msg: The message the log.
        :param namespace: A log prefix, generally the module ``__name__`` that
            the log is coming from.  Will default to self._meta.namespace if
            None is passed.  For debugging, it can be useful to set this to
            ``__file__``, though ``__name__`` is much less verbose.
        :keyword kw: Keyword arguments are passed on to the backend logging
            system.

        """
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.debug(msg, **kwargs)


def load(app):
    handler.register(LoggingLogHandler)
