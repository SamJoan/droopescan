"""Plugin Framework Extension"""

import os
import sys
import glob
import importlib.util
import importlib.machinery
from ..core import backend, handler, plugin, exc
from ..utils.misc import is_true, minimal_logger
from ..utils.fs import abspath

LOG = minimal_logger(__name__)

# FIX ME: This is a redundant name... ?


class CementPluginHandler(plugin.CementPluginHandler):

    """
    This class is an internal implementation of the
    :ref:`IPlugin <cement.core.plugin>` interface. It does not take any
    parameters on initialization.

    """

    class Meta:

        """Handler meta-data."""

        interface = plugin.IPlugin
        """The interface that this class implements."""

        label = 'cement'
        """The string identifier for this class."""

    def __init__(self):
        super(CementPluginHandler, self).__init__()
        self._loaded_plugins = []
        self._enabled_plugins = []
        self._disabled_plugins = []
        self._plugin_configs = {}

    def _setup(self, app_obj):
        super(CementPluginHandler, self)._setup(app_obj)
        self._enabled_plugins = []
        self._disabled_plugins = []
        self._plugin_configs = {}
        self.config_dirs = self.app._meta.plugin_config_dirs
        self.bootstrap = self.app._meta.plugin_bootstrap
        self.load_dirs = self.app._meta.plugin_dirs

        # grab a generic config handler object
        config_handler = handler.get('config', self.app.config._meta.label)

        # first parse plugin config dir for enabled plugins
        for config_dir in self.config_dirs:
            config_dir = abspath(config_dir)

            if not os.path.exists(config_dir):
                LOG.debug('plugin config dir %s does not exist.' %
                          config_dir)
                continue
            else:
                # sort so that we always load plugins in the same order
                # regardless of OS (seems some don't sort reliably)
                plugin_config_files = glob.glob("%s/*.conf" % config_dir)
                plugin_config_files.sort()

                for config in plugin_config_files:
                    config = os.path.abspath(os.path.expanduser(config))
                    LOG.debug("loading plugin config from '%s'." % config)
                    pconfig = config_handler()
                    pconfig._setup(self.app)
                    pconfig.parse_file(config)

                    if not pconfig.get_sections():
                        LOG.debug("config file '%s' has no sections." %
                                  config)
                        continue

                    plugin = pconfig.get_sections()[0]
                    if 'enable_plugin' not in pconfig.keys(plugin):
                        continue

                    if is_true(pconfig.get(plugin, 'enable_plugin')):
                        LOG.debug("enabling plugin '%s' per plugin config" %
                                  plugin)
                        if plugin not in self._enabled_plugins:
                            self._enabled_plugins.append(plugin)
                        if plugin in self._disabled_plugins:
                            self._disabled_plugins.remove(plugin)
                    else:
                        LOG.debug("disabling plugin '%s' per plugin config" %
                                  plugin)
                        if plugin not in self._disabled_plugins:
                            self._disabled_plugins.append(plugin)
                        if plugin in self._enabled_plugins:
                            self._enabled_plugins.remove(plugin)

                    # Store the config for later use in load_plugin()
                    # NOTE: Store the config regardless of whether it is
                    # enabled or disabled
                    if plugin not in self._plugin_configs.keys():
                        self._plugin_configs[plugin] = {}

                    for key in pconfig.keys(plugin):
                        val = pconfig.get(plugin, key)
                        self._plugin_configs[plugin][key] = val

        # second, parse all app configs for plugins. Note: these are already
        # loaded from files when app.config was setup.  The application
        # configuration OVERRIDES plugin configs.
        for plugin in self.app.config.get_sections():
            if 'enable_plugin' not in self.app.config.keys(plugin):
                continue
            if is_true(self.app.config.get(plugin, 'enable_plugin')):
                LOG.debug("enabling plugin '%s' per application config" %
                          plugin)
                if plugin not in self._enabled_plugins:
                    self._enabled_plugins.append(plugin)
                if plugin in self._disabled_plugins:
                    self._disabled_plugins.remove(plugin)
            else:
                LOG.debug("disabling plugin '%s' per application config" %
                          plugin)
                if plugin not in self._disabled_plugins:
                    self._disabled_plugins.append(plugin)
                if plugin in self._enabled_plugins:
                    self._enabled_plugins.remove(plugin)

    def _load_plugin_from_dir(self, plugin_name, plugin_dir):
        """
        Load a plugin from file within a plugin directory rather than a
        python package within sys.path.

        :param plugin_name: The name of the plugin, also the name of the file
            with '.py' appended to the name.
        :param plugin_dir: The filesystem directory path where to find the
            file.

        """
        full_path = os.path.join(plugin_dir, "%s.py" % plugin_name)
        if not os.path.exists(full_path):
            LOG.debug("plugin file '%s' does not exist." % full_path)
            return False

        LOG.debug("attempting to load '%s' from '%s'" % (plugin_name,
                                                         plugin_dir))

        # We don't catch this because it would make debugging a nightmare
       # f, path, desc = imp.find_module(plugin_name, [plugin_dir])
       # mod = imp.load_module(plugin_name, f, path, desc)
       # if mod and hasattr(mod, 'load'):
       #     mod.load(self.app)
       # return True
        plugin_path = os.path.join(plugin_dir, plugin_name + ".py")
        spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        if hasattr(mod, 'load'):
                mod.load(self.app)
        return True 

    def _load_plugin_from_bootstrap(self, plugin_name, base_package):
        """
        Load a plugin from a python package.  Returns True if no ImportError
        is encountered.

        :param plugin_name: The name of the plugin, also the name of the
            module to load from base_package.
            I.e. ``myapp.bootstrap.myplugin``
        :type plugin_name: str
        :param base_package: The base python package to load the plugin module
            from.  I.e.'myapp.bootstrap' or similar.
        :type base_package: str
        :returns: True is the plugin was loaded, False otherwise
        :raises: ImportError

        """

        full_module = '%s.%s' % (base_package, plugin_name)

        # If the base package doesn't exist, we return False rather than
        # bombing out.
        if base_package not in sys.modules:
            try:
                __import__(base_package, globals(), locals(), [], 0)
            except ImportError as e:
                LOG.debug("unable to import plugin bootstrap module '%s'."
                          % base_package)
                return False

        LOG.debug("attempting to load '%s' from '%s'" % (plugin_name,
                                                         base_package))
        # We don't catch this because it would make debugging a nightmare
        if full_module not in sys.modules:
            __import__(full_module, globals(), locals(), [], 0)

        if hasattr(sys.modules[full_module], 'load'):
            sys.modules[full_module].load(self.app)

        return True

    def load_plugin(self, plugin_name):
        """
        Load a plugin whose name is 'plugin_name'.  First attempt to load
        from a plugin directory (plugin_dir), secondly attempt to load from a
        bootstrap module (plugin_bootstrap) determined by
        self.app._meta.plugin_bootstrap.

        Upon successful loading of a plugin, the plugin name is appended to
        the self._loaded_plugins list.

        :param plugin_name: The name of the plugin to load.
        :type plugin_name: str
        :raises: cement.core.exc.FrameworkError

        """
        LOG.debug("loading application plugin '%s'" % plugin_name)

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
            raise exc.FrameworkError("Unable to load plugin '%s'." %
                                     plugin_name)

        # Merge in missing config settings (app config settings take
        # precedence):
        #
        # Note that we loaded the plugin configs during _setup() into
        # self._plugin_configs... yes, this is fucking dirty.
        if plugin_name not in self.app.config.get_sections():
            self.app.config.add_section(plugin_name)

        if plugin_name in self._plugin_configs.keys():
            plugin_config = self._plugin_configs[plugin_name]
            for key, val in plugin_config.items():
                if key not in self.app.config.keys(plugin_name):
                    self.app.config.set(plugin_name, key, val)

    def load_plugins(self, plugin_list):
        """
        Load a list of plugins.  Each plugin name is passed to
        self.load_plugin().

        :param plugin_list: A list of plugin names to load.

        """
        for plugin_name in plugin_list:
            self.load_plugin(plugin_name)

    def get_loaded_plugins(self):
        """List of plugins that have been loaded."""
        return self._loaded_plugins

    def get_enabled_plugins(self):
        """List of plugins that are enabled (not necessary loaded yet)."""
        return self._enabled_plugins

    def get_disabled_plugins(self):
        """List of disabled plugins"""
        return self._disabled_plugins


def load(app):
    handler.register(CementPluginHandler)
