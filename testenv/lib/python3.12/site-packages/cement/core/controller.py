"""Cement core controller module."""

from __future__ import annotations
from abc import abstractmethod
from typing import Any, Union
from ..core.interface import Interface
from ..core.handler import Handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class ControllerInterface(Interface):

    """
    This class defines the Controller Interface.  Handlers that implement this
    interface must provide the methods and attributes defined below. In
    general, most implementations should sub-class from the provided
    :class:`ControllerHandler` base class as a starting point.
    """

    class Meta(Interface.Meta):

        """Interface meta-data."""

        #: The string identifier of the interface.
        interface = 'controller'

    @abstractmethod
    def _dispatch(self) -> Union[Any | None]:
        """
        Reads the application object's data to dispatch a command from this
        controller.  For example, reading ``self.app.pargs`` to determine what
        command was passed, and then executing that command function.

        Note that Cement does *not* parse arguments when calling
        ``_dispatch()`` on a controller, as it expects the controller to
        handle parsing arguments (I.e. ``self.app.args.parse()``).

        Returns:
            unknown: The result of the executed controller function, or
            ``None`` if no controller function is called.

        """
        pass    # pragma: nocover


class ControllerHandler(ControllerInterface, Handler):
    """Controller handler implementation."""
    class Meta(Handler.Meta):
        pass    # pragma: nocover
