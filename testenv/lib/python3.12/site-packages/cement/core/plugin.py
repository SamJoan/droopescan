"""Cement core plugins module."""

from abc import abstractmethod
from typing import List
from ..core.interface import Interface
from ..core.handler import Handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class PluginInterface(Interface):

    """
    This class defines the Plugin Interface.  Handlers that implement this
    interface must provide the methods and attributes defined below. In
    general, most implementations should sub-class from the provided
    :class:`PluginHandler` base class as a starting point.
    """

    class Meta(Interface.Meta):

        #: String identifier of the interface.
        interface = 'plugin'

    @abstractmethod
    def load_plugin(self, plugin_name: str) -> None:
        """
        Load a plugin whose name is ``plugin_name``.

        Args:
            plugin_name (str): The name of the plugin to load.

        """
        pass  # pragma: nocover

    @abstractmethod
    def load_plugins(self, plugins: List[str]) -> None:
        """
        Load all plugins from ``plugins``.

        Args:
            plugins (list): A list of plugin names to load.

        """
        pass  # pragma: nocover

    @abstractmethod
    def get_loaded_plugins(self) -> List[str]:
        """Returns a list of plugins that have been loaded."""
        pass  # pragma: nocover

    @abstractmethod
    def get_enabled_plugins(self) -> List[str]:
        """Returns a list of plugins that are enabled in the config."""
        pass  # pragma: nocover

    @abstractmethod
    def get_disabled_plugins(self) -> List[str]:
        """Returns a list of plugins that are disabled in the config."""
        pass  # pragma: nocover


class PluginHandler(PluginInterface, Handler):

    """
    Plugin handler implementation.

    """

    class Meta(Handler.Meta):
        pass  # pragma: nocover
