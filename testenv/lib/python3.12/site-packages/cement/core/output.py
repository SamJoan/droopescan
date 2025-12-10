"""Cement core output module."""

from abc import abstractmethod
from typing import Any, Dict, Union
from ..core.interface import Interface
from ..core.handler import Handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class OutputInterface(Interface):

    """
    This class defines the Output Interface.  Handlers that implement this
    interface must provide the methods and attributes defined below. In
    general, most implementations should sub-class from the provided
    :class:`OutputHandler` base class as a starting point.
    """

    class Meta(Interface.Meta):

        """Handler meta-data."""

        #: The string identifier of the interface
        interface = 'output'

    @abstractmethod
    def render(self, data: Dict[str, Any], *args: Any, **kwargs: Any) -> Union[str, None]:
        """
        Render the ``data`` dict into output in some fashion.  This function
        must accept both ``*args`` and ``**kwargs`` to allow an application to
        mix output handlers that support different features.

        Args:
            data (dict): The dictionary whose data we need to render into
                output.

        Returns:
            str, None: The rendered output string, or ``None`` if no output is
            rendered

        """
        pass  # pragma: nocover


class OutputHandler(OutputInterface, Handler):

    """Output handler implementation."""

    class Meta(Handler.Meta):
        pass  # pragma: nocover
