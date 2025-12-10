"""
Cement plugin extension module.
"""

from __future__ import annotations
import os
import sys
import importlib
import importlib.util
import importlib.machinery
import re
from typing import List, TYPE_CHECKING
from ..core import plugin, exc
from ..utils.misc import is_true, minimal_logger
from ..utils.fs import abspath

if TYPE_CHECKING:
    from ..core.foundation import App  # pragma: nocover

LOG = minimal_logger(__name__)

# FIX ME: This is a redundant name... ?


class CementPluginHandler(plugin.PluginHandler):

    """
    This class is an internal implementation of the
    :ref:`IPlugin <cement.core.plugin>` interface. It does not take any
    parameters on initialization.

    """

    class Meta(plugin.PluginHandler.Meta):

        """Handler meta-data."""

        label = 'cement'
        """The string identifier for this class."""

    _meta: Meta  # type: ignore

    def __init__(self) -> None:
        super().__init__()
        self._loaded_plugins: List[str] = []
        self._enabled_plugins: List[str] = []
        self._disabled_plugins: List[str] = []

    def _setup(self, app_obj: App) -> None:
        super()._setup(app_obj)
        self._enabled_plugins = []
        self._disabled_plugins = []
        self.bootstrap = self.app._meta.plugin_module
        self.load_dirs = self.app._meta.plugin_dirs

        # parse all app configs for plugins. Note: these are already
        # loaded from files when app.config was setup.  The application
        # configuration OVERRIDES plugin configs.
        for section in self.app.config.get_sections():
            if not section.startswith('plugin.'):
                continue
            plugin_section = section
            plugin = re.sub('^plugin.', '', section)

            if 'enabled' not in self.app.config.keys(plugin_section):
                continue
            if is_true(self.app.config.get(plugin_section, 'enabled')):
                LOG.debug(f"enabling plugin '{plugin}' per application config")
                if plugin not in self._enabled_plugins:
                    self._enabled_plugins.append(plugin)  # pragma: nocover
                if plugin in self._disabled_plugins:
                    self._disabled_plugins.remove(plugin)  # pragma: nocover
            else:
                LOG.debug(f"disabling plugin '{plugin}' per application config")
                if plugin not in self._disabled_plugins:
                    self._disabled_plugins.append(plugin)  # pragma: nocover
                if plugin in self._enabled_plugins:
                    self._enabled_plugins.remove(plugin)  # pragma: nocover

    def _load_plugin_from_dir(self, plugin_name: str, plugin_dir: str) -> bool:
        """
        Load a plugin from a directory path rather than a python package
        within sys.path.  This would either be ``myplugin.py`` or
        ``myplugin/__init__.py`` within the given ``plugin_dir``.

        Args:
            plugin_name (str): The name of the plugin.
            plugin_dir (str): The filesystem directory path where the plugin
                exists.

        Returns:
            bool: ``True`` is the plugin was loaded, ``False`` otherwise.

        """
        LOG.debug(f"attempting to load '{plugin_name}' from '{plugin_dir}'")

        if not os.path.exists(plugin_dir):
            LOG.debug(f"plugin directory '{plugin_dir}' does not exist.")
            return False

        spec = importlib.machinery.PathFinder().find_spec(
            plugin_name, [plugin_dir]
        )
        if not spec:
            LOG.debug(f"plugin '{plugin_name}' does not exist in '{plugin_dir}'.")
            return False

        # We don't catch this because it would make debugging a
        # nightmare
        mod = importlib.util.module_from_spec(spec)
        sys.modules[plugin_name] = mod
        spec.loader.exec_module(mod)  # type: ignore

        if mod and hasattr(mod, 'load'):
            mod.load(self.app)
        return True

    def _load_plugin_from_bootstrap(self, plugin_name: str, base_package: str) -> bool:
        """
        Load a plugin from a python package.  Returns True if no ImportError
        is encountered.

        Args:
            plugin_name (str): The name of the plugin, also the name of the
                module to load from base_package. I.e.
                ``myapp.bootstrap.myplugin``
            base_package (str): The base python package to load the plugin module
                from.  I.e. ``myapp.bootstrap`` or similar.

        Returns:
            bool: ``True`` is the plugin was loaded, ``False`` otherwise.

        Raises:
            :py:class:`ImportError`: If the plugin can not be imported

        """

        full_module = f'{base_package}.{plugin_name}'

        # If the base package doesn't exist, we return False rather than
        # bombing out.
        if base_package not in sys.modules:
            try:
                __import__(base_package, globals(), locals(), [], 0)
            except ImportError:
                LOG.debug(f"unable to import plugin bootstrap module '{base_package}'.")
                return False

        LOG.debug(f"attempting to load '{plugin_name}' from '{base_package}'")
        # We don't catch this because it would make debugging a nightmare
        # FIXME: not sure how to test/cover this
        if full_module not in sys.modules:
            __import__(full_module,
                       globals(), locals(), [], 0)  # pragma: nocover

        if hasattr(sys.modules[full_module], 'load'):
            sys.modules[full_module].load(self.app)

        return True

    def load_plugin(self, plugin_name: str) -> None:
        """
        Load a plugin whose name is ``plugin_name``.  First attempt to load
        from a plugin directory (plugin_dir), secondly attempt to load from a
        Python module determined by ``App.Meta.plugin_module``.

        Upon successful loading of a plugin, the plugin name is appended to
        the ``self._loaded_plugins list``.

        Args:
            plugin_name (str): The name of the plugin to load.

        Raises:
            cement.core.exc.FrameworkError: If the plugin can not be loaded

        """
        LOG.debug(f"loading application plugin '{plugin_name}'")

        # first attempt to load from plugin_dirs
        for load_dir in self.load_dirs:
            load_dir = abspath(load_dir)

            if self._load_plugin_from_dir(plugin_name, load_dir):
                self._loaded_plugins.append(plugin_name)
                break

        # then from a bootstrap module
        if plugin_name not in self._loaded_plugins:
            if self._load_plugin_from_bootstrap(plugin_name, self.bootstrap):
                self._loaded_plugins.append(plugin_name)

        # otherwise it's a bust
        if plugin_name not in self._loaded_plugins:
            raise exc.FrameworkError(f"Unable to load plugin '{plugin_name}'.")

    def load_plugins(self, plugin_list: List[str]) -> None:
        """
        Load a list of plugins.  Each plugin name is passed to
        ``self.load_plugin()``.

        Args:
            plugin_list (list): A list of plugin names to load.

        """
        for plugin_name in plugin_list:
            self.load_plugin(plugin_name)

    def get_loaded_plugins(self) -> List[str]:
        """List of plugins that have been loaded."""
        return self._loaded_plugins

    def get_enabled_plugins(self) -> List[str]:
        """List of plugins that are enabled (not necessary loaded yet)."""
        return self._enabled_plugins

    def get_disabled_plugins(self) -> List[str]:
        """List of disabled plugins"""
        return self._disabled_plugins


def load(app: App) -> None:
    app.handler.register(CementPluginHandler)
