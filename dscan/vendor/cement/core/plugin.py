"""Cement core plugins module."""

from ..core import backend, exc, interface, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


def plugin_validator(klass, obj):
    """Validates an handler implementation against the IPlugin interface."""

    members = [
        '_setup',
        'load_plugin',
        'load_plugins',
        'get_loaded_plugins',
        'get_enabled_plugins',
        'get_disabled_plugins',
    ]
    interface.validate(IPlugin, obj, members)


class IPlugin(interface.Interface):

    """
    This class defines the Plugin Handler Interface.  Classes that
    implement this handler must provide the methods and attributes defined
    below.

    Implementations do *not* subclass from interfaces.

    Usage:

    .. code-block:: python

        from cement.core import plugin

        class MyPluginHandler(object):
            class Meta:
                interface = plugin.IPlugin
                label = 'my_plugin_handler'
            ...

    """
    # pylint: disable=W0232, C0111, R0903
    class IMeta:
        label = 'plugin'
        validator = plugin_validator

    # Must be provided by the implementation
    Meta = interface.Attribute('Handler meta-data')

    def _setup(app_obj):
        """
        The _setup function is called during application initialization and
        must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object.

        """

    def load_plugin(plugin_name):
        """
        Load a plugin whose name is 'plugin_name'.

        :param plugin_name: The name of the plugin to load.

        """

    def load_plugins(plugin_list):
        """
        Load all plugins from plugin_list.

        :param plugin_list: A list of plugin names to load.

        """

    def get_loaded_plugins():
        """Returns a list of plugins that have been loaded."""

    def get_enabled_plugins():
        """Returns a list of plugins that are enabled in the config."""

    def get_disabled_plugins():
        """Returns a list of plugins that are disabled in the config."""


class CementPluginHandler(handler.CementBaseHandler):

    """
    Base class that all Plugin Handlers should sub-class from.

    """

    class Meta:

        """
        Handler meta-data (can be passed as keyword arguments to the parent
        class).
        """

        label = None
        """The string identifier of this handler."""

        interface = IPlugin
        """The interface that this class implements."""

    def __init__(self, *args, **kw):
        super(CementPluginHandler, self).__init__(*args, **kw)
