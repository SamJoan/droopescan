"""
Cement logging extension module.
"""

from __future__ import annotations
import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Union, Optional, Type, TYPE_CHECKING
from ..core import log
from ..core.deprecations import deprecate
from ..utils.misc import is_true, minimal_logger
from ..utils import fs

if TYPE_CHECKING:
    from ..core.foundation import App  # pragma: nocover


LOG = minimal_logger(__name__)

try:                                                                 # pragma: no cover
    NullHandler = logging.NullHandler                                # pragma: no cover
except AttributeError:                                               # pragma: no cover
    # Not supported on Python < 3.1/2.7                              # pragma: no cover
    class NullHandler(logging.Handler):             # type: ignore   # pragma: no cover

        def handle(self, record):                   # type: ignore   # pragma: no cover
            pass                                                     # pragma: no cover

        def emit(self, record):                     # type: ignore   # pragma: no cover
            pass                                                     # pragma: no cover

        def createLock(self):                       # type: ignore   # pragma: no cover
            self.lock = None                                         # pragma: no cover


class LoggingLogHandler(log.LogHandler):

    """
    This class is an implementation of the :ref:`Log <cement.core.log>`
    interface, and sets up the logging facility using the standard Python
    `logging <http://docs.python.org/library/logging.html>`_ module.

    """

    class Meta(log.LogHandler.Meta):

        """Handler meta-data."""

        #: The string identifier of this handler.
        label = 'logging'

        #: The logging namespace.
        #:
        #: Note: Although Meta.namespace defaults to None, Cement will set
        #: this to the application label (App.Meta.label) if not set
        #: during setup.
        namespace: str = None  # type: ignore

        #: Class to use as the formatter
        formatter_class: Type = logging.Formatter

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
        clear_loggers: List[str] = []

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

        #: List of arguments to use for the cli options
        #: (ex: [``-l``, ``--list``]).  If a log-level argument is not wanted,
        #: set to ``None`` (default).
        log_level_argument: Optional[List[str]] = None

        #: The help description for the log level argument
        log_level_argument_help = 'logging level'

        #: Whether or not to propagate logs up to parents. Likely should
        #: always be ``False``, but is here in the off chance this breaks
        #: something. Setting to ``False`` resolves situations where duplicate
        #: logs appear with other libraries who logged to the root logger.
        #:
        #: Note, if attempting to use PyTest ``caplog`` fixture, this may need
        #: to be set to ``True``.
        #:
        #: See: ``tests.ext.test_ext_colorlog.test_colorlog``.
        propagate = False

    _meta: Meta  # type: ignore

    levels = ['INFO', 'WARNING', 'ERROR', 'DEBUG', 'FATAL', 'CRITICAL']

    def __init__(self, *args: Any, **kw: Any) -> None:
        super(LoggingLogHandler, self).__init__(*args, **kw)
        self.app: App = None  # type: ignore

    def _setup(self, app_obj: App) -> None:
        super(LoggingLogHandler, self)._setup(app_obj)
        if self._meta.namespace is None:
            self._meta.namespace = f"{self.app._meta.label}"

        self.backend = logging.getLogger(f"cement:app:{self._meta.namespace}")

        # hack for application debugging
        if is_true(self.app._meta.debug):
            self.app.config.set(self._meta.config_section, 'level', 'DEBUG')

        level = self.app.config.get(self._meta.config_section, 'level')
        self.set_level(level)
        self.backend.propagate = self._meta.propagate

        LOG.debug("logging initialized for '%s' using %s" %
                  (self._meta.namespace, self.__class__.__name__))

    def set_level(self, level: str) -> None:
        """
        Set the log level.  Must be one of the log levels configured in
        self.levels which are
        ``['INFO', 'WARNING', 'ERROR', 'DEBUG', 'FATAL', 'CRITICAL]``.

        As of Cement 3.0.10, the FATAL facility is deprecated and will be
        removed in future versions of Cement. Please us `CRITICAL` instead.

        :param level: The log level to set.

        """
        self.clear_loggers(self._meta.namespace)
        for namespace in self._meta.clear_loggers:
            self.clear_loggers(namespace)

        level = level.upper()

        if level not in self.levels:
            level = 'INFO'

        if level == 'FATAL':
            deprecate('3.0.10-1')

        level = getattr(logging, level.upper())

        self.backend.setLevel(level)

        # console
        self._setup_console_log()

        # file
        self._setup_file_log()

    def get_level(self) -> str:
        """Returns the current log level."""
        return logging.getLevelName(self.backend.level)

    def clear_loggers(self, namespace: str) -> None:
        """Clear any previously configured loggers for ``namespace``."""

        for i in logging.getLogger(f"cement:app:{namespace}").handlers:
            logging.getLogger(f"cement:app:{namespace}").removeHandler(i)

        self.backend = logging.getLogger(f"cement:app:{namespace}")

    def _get_console_format(self) -> str:
        if self.get_level() == logging.getLevelName(logging.DEBUG):
            format = self._meta.debug_format
        else:
            format = self._meta.console_format

        return format

    def _get_file_format(self) -> str:
        if self.get_level() == logging.getLevelName(logging.DEBUG):
            format = self._meta.debug_format
        else:
            format = self._meta.file_format

        return format

    def _get_file_formatter(self, format: str) -> logging.Formatter:
        return self._meta.formatter_class(format)  # type: ignore

    def _get_console_formatter(self, format: str) -> logging.Formatter:
        return self._meta.formatter_class(format)  # type: ignore

    def _setup_console_log(self) -> None:
        """Add a console log handler."""
        namespace = self._meta.namespace
        to_console = self.app.config.get(self._meta.config_section,
                                         'to_console')
        console_handler: Union[logging.StreamHandler, NullHandler]
        if is_true(to_console):
            console_handler = logging.StreamHandler()
            format = self._get_console_format()
            formatter = self._get_console_formatter(format)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(getattr(logging, self.get_level()))
        else:
            console_handler = NullHandler()

        # FIXME: self._clear_loggers() should be preventing this but it's not!
        for i in logging.getLogger(f"cement:app:{namespace}").handlers:
            if isinstance(i, logging.StreamHandler):
                self.backend.removeHandler(i)

        self.backend.addHandler(console_handler)

    def _setup_file_log(self) -> None:
        """Add a file log handler."""

        namespace = self._meta.namespace
        file_path = self.app.config.get(self._meta.config_section, 'file')
        rotate = self.app.config.get(self._meta.config_section, 'rotate')
        max_bytes = self.app.config.get(self._meta.config_section,
                                        'max_bytes')
        max_files = self.app.config.get(self._meta.config_section,
                                        'max_files')
        file_handler: Union[logging.FileHandler, RotatingFileHandler, NullHandler]

        if file_path:
            file_path = fs.abspath(file_path)
            log_dir = os.path.dirname(file_path)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            if rotate:
                file_handler = RotatingFileHandler(
                    file_path,
                    maxBytes=int(max_bytes),
                    backupCount=int(max_files),
                )
            else:
                file_handler = logging.FileHandler(file_path)

            format = self._get_file_format()
            formatter = self._get_file_formatter(format)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(getattr(logging, self.get_level()))
        else:
            file_handler = NullHandler()

        # FIXME: self._clear_loggers() should be preventing this but it's not!
        for i in logging.getLogger(f"cement:app:{namespace}").handlers:
            if isinstance(i, file_handler.__class__):   # pragma: nocover
                self.backend.removeHandler(i)           # pragma: nocover

        self.backend.addHandler(file_handler)

    def _get_logging_kwargs(self, namespace: Optional[str], **kw: Any) -> Dict[str, Any]:
        if namespace is None:
            namespace = self._meta.namespace

        if 'extra' in kw.keys() and 'namespace' in kw['extra'].keys():
            pass
        elif 'extra' in kw.keys() and 'namespace' not in kw['extra'].keys():
            kw['extra']['namespace'] = namespace
        else:
            kw['extra'] = dict(namespace=namespace)

        return kw

    def info(self, msg: str, namespace: Optional[str] = None, **kw: Any) -> None:
        """
        Log to the INFO facility.

        Args:
            msg (str): The message to log.

        Keyword Args:
            namespace (str): A log prefix, generally the module ``__name__``
                that the log is coming from.  Will default to
                ``self._meta.namespace`` if none is passed.

        Other Parameters:
            kwargs: Keyword arguments are passed on to the backend logging
                system.

        """
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.info(msg, **kwargs)

    def warning(self, msg: str, namespace: Optional[str] = None, **kw: Any) -> None:
        """
        Log to the WARNING facility.

        Args:
            msg (str): The message to log.

        Keyword Args:
            namespace (str): A log prefix, generally the module ``__name__``
                that the log is coming from.  Will default to
                ``self._meta.namespace`` if none is passed.

        Other Parameters:
            kwargs: Keyword arguments are passed on to the backend logging
                system.

        """
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.warning(msg, **kwargs)

    def error(self, msg: str, namespace: Optional[str] = None, **kw: Any) -> None:
        """
        Log to the ERROR facility.

        :Args:
            msg (str): The message to log.

        Keyword Args:
            namespace (str): A log prefix, generally the module ``__name__``
                that the log is coming from.  Will default to
                ``self._meta.namespace`` if none is passed.

        Other Parameters:
            kwargs: Keyword arguments are passed on to the backend logging
                system.

        """
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.error(msg, **kwargs)

    def critical(self, msg: str, namespace: Optional[str] = None, **kw: Any) -> None:
        """
        Log to the CRITICAL facility.

        Args:
            msg (str): The message to log.

        Keyword Args:
            namespace (str): A log prefix, generally the module ``__name__``
                that the log is coming from.  Will default to
                ``self._meta.namespace`` if none is passed.

        Other Parameters:
            kwargs: Keyword arguments are passed on to the backend logging
                system.

        """
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.critical(msg, **kwargs)

    def fatal(self, msg: str, namespace: Optional[str] = None, **kw: Any) -> None:
        """
        Log to the FATAL (aka CRITICAL) facility.

        As of Cement 3.0.10, this method is deprecated and will be removed in
        future versions of Cement. Please us `critical()` instead.

        Args:
            msg (str): The message to log.

        Keyword Args:
            namespace (str): A log prefix, generally the module ``__name__``
                that the log is coming from.  Will default to
                ``self._meta.namespace`` if none is passed.

        Other Parameters:
            kwargs: Keyword arguments are passed on to the backend logging
                system.

        """
        deprecate('3.0.10-1')
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.fatal(msg, **kwargs)

    def debug(self, msg: str, namespace: Optional[str] = None, **kw: Any) -> None:
        """
        Log to the DEBUG facility.

        Args:
            msg (str): The message to log.

        Keyword Args:
            namespace (str): A log prefix, generally the module ``__name__``
                that the log is coming from.  Will default to
                ``self._meta.namespace`` if none is passed.

        Other Parameters:
            kwargs: Keyword arguments are passed on to the backend logging
                system.

        """
        kwargs = self._get_logging_kwargs(namespace, **kw)
        self.backend.debug(msg, **kwargs)


def add_logging_arguments(app: App) -> None:
    if app.log._meta.log_level_argument is not None:
        app.args.add_argument(*app.log._meta.log_level_argument,
                              dest='log_logging_level',
                              help=app.log._meta.log_level_argument_help,
                              choices=[x.lower() for x in app.log.levels])


def handle_logging_arguments(app: App) -> None:
    if hasattr(app.pargs, 'log_logging_level'):
        if app.pargs.log_logging_level is not None:
            app.log.set_level(app.pargs.log_logging_level)
        if app.pargs.log_logging_level in ['debug', 'DEBUG']:
            app._meta.debug = True


def load(app: App) -> None:
    app.handler.register(LoggingLogHandler)
    app.hook.register('pre_argument_parsing', add_logging_arguments)
    app.hook.register('post_argument_parsing', handle_logging_arguments)
