"""
Cement core log module.

"""

from ..core import exc, interface, handler


def log_validator(klass, obj):
    """Validates an handler implementation against the ILog interface."""

    members = [
        '_setup',
        'set_level',
        'get_level',
        'info',
        'warn',
        'error',
        'fatal',
        'debug',
    ]
    interface.validate(ILog, obj, members)


class ILog(interface.Interface):

    """
    This class defines the Log Handler Interface.  Classes that
    implement this handler must provide the methods and attributes defined
    below.

    Implementations do *not* subclass from interfaces.

    Usage:

    .. code-block:: python

        from cement.core import log

        class MyLogHandler(object):
            class Meta:
                interface = log.ILog
                label = 'my_log_handler'
            ...

    """

    # pylint: disable=W0232, C0111, R0903
    class IMeta:

        """Interface meta-data."""

        label = 'log'
        """The string identifier of the interface."""

        validator = log_validator
        """The interface validator function."""

    # Must be provided by the implementation
    Meta = interface.Attribute('Handler Meta-data')

    def _setup(app_obj):
        """
        The _setup function is called during application initialization and
        must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object.

        """

    def set_level():
        """
        Set the log level.  Must except atleast one of:
            ``['INFO', 'WARN', 'ERROR', 'DEBUG', or 'FATAL']``.

        """

    def get_level():
        """Return a string representation of the log level."""

    def info(msg):
        """
        Log to the 'INFO' facility.

        :param msg: The message to log.

        """

    def warn(self, msg):
        """
        Log to the 'WARN' facility.

        :param msg: The message to log.

        """

    def error(self, msg):
        """
        Log to the 'ERROR' facility.

        :param msg: The message to log.

        """

    def fatal(self, msg):
        """
        Log to the 'FATAL' facility.

        :param msg: The message to log.

        """

    def debug(self, msg):
        """
        Log to the 'DEBUG' facility.

        :param msg: The message to log.

        """


class CementLogHandler(handler.CementBaseHandler):

    """
    Base class that all Log Handlers should sub-class from.

    """

    class Meta:

        """
        Handler meta-data (can be passed as keyword arguments to the parent
        class).
        """

        label = None
        """The string identifier of this handler."""

        interface = ILog
        """The interface that this class implements."""

    def __init__(self, *args, **kw):
        super(CementLogHandler, self).__init__(*args, **kw)
