"""
Cement core log module.

"""

# from ..core import interface
from abc import abstractmethod
from ..core.interface import Interface
from ..core.handler import Handler


class LogInterface(Interface):

    """
    This class defines the Log Interface.  Handlers that implement this
    interface must provide the methods and attributes defined below. In
    general, most implementations should sub-class from the provided
    :class:`LogHandler` base class as a starting point.
    """

    class Meta(Interface.Meta):

        """Handler meta-data."""

        #: The string identifier of the interface.
        interface = 'log'

    @abstractmethod
    def set_level(self, level: str) -> None:
        """
        Set the log level.  Must except atleast one of:
            ``['INFO', 'WARNING', 'ERROR', 'DEBUG', or 'FATAL']``.

        """
        pass  # pragma: nocover

    @abstractmethod
    def get_level(self) -> str:
        """Return a string representation of the log level."""
        pass  # pragma: nocover

    @abstractmethod
    def info(self, msg: str) -> None:
        """
        Log to the ``INFO`` facility.

        Args:
            msg (str): The message to log.

        """
        pass  # pragma: nocover

    @abstractmethod
    def warning(self, msg: str) -> None:
        """
        Log to the ``WARNING`` facility.

        Args:
            msg (str): The message to log.

        """
        pass  # pragma: nocover

    @abstractmethod
    def error(self, msg: str) -> None:
        """
        Log to the ``ERROR`` facility.

        Args:
            msg (str): The message to log.

        """
        pass  # pragma: nocover

    @abstractmethod
    def fatal(self, msg: str) -> None:
        """
        Log to the ``FATAL`` facility.

        Args:
            msg (str): The message to log.

        """
        pass  # pragma: nocover

    @abstractmethod
    def debug(self, msg: str) -> None:
        """
        Log to the ``DEBUG`` facility.

        Args:
            msg (str): The message to log.

        """
        pass  # pragma: nocover


class LogHandler(LogInterface, Handler):

    """
    Log handler implementation.

    """

    class Meta(Handler.Meta):
        pass  # pragma: nocover
