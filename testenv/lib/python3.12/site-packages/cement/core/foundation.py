"""Cement core foundation module."""

from __future__ import annotations
import os
import platform
import signal
import sys
from importlib import reload as reload_module
from time import sleep
from typing import (IO, Any, Callable, Dict, List, Optional, TextIO, Tuple,
                    Type, Union, TYPE_CHECKING)
from ..core import (arg, cache, config, controller, exc, extension, log, mail,
                    meta, output, plugin, template)
from ..core.deprecations import deprecate
from ..core.handler import Handler, HandlerManager
from ..core.hook import HookManager
from ..core.interface import Interface, InterfaceManager
from ..ext.ext_argparse import ArgparseController as Controller
from ..utils import fs, misc
from ..utils.misc import is_true, minimal_logger

if TYPE_CHECKING:
    from types import FrameType, ModuleType, TracebackType  # pragma: nocover


ArgparseArgumentType = Tuple[List[str], Dict[str, Any]]

join = os.path.join


LOG = minimal_logger(__name__)
if platform.system() == 'Windows':
    SIGNALS = [signal.SIGTERM, signal.SIGINT]   # pragma: nocover
else:
    SIGNALS = [signal.SIGTERM, signal.SIGINT, signal.SIGHUP]


def add_handler_override_options(app: App) -> None:
    """
    This is a ``post_setup`` hook that adds the handler override options to
    the argument parser

    Args:
        app (instance): The application object

    """
    if app._meta.handler_override_options is None:
        return

    for i in app._meta.handler_override_options:
        if i not in app.interface.list():
            LOG.debug(f"interface '{i}'" +
                      " is not defined, can not override handlers")
            continue

        if len(app.handler.list(i)) > 1:
            handlers = []
            for h in app.handler.list(i):
                handlers.append(app._resolve_handler(i, h))

            choices = [x._meta.label
                       for x in handlers
                       if x._meta.overridable is True]

            # don't display the option if no handlers are overridable
            if not len(choices) > 0:
                LOG.debug("no handlers are overridable within the " +
                          f"{i} interface")
                continue

            # override things that we need to control
            argument_kw = app._meta.handler_override_options[i][1]
            argument_kw['dest'] = f'{i}_handler_override'
            argument_kw['action'] = 'store'
            argument_kw['choices'] = choices

            app.args.add_argument(
                *app._meta.handler_override_options[i][0],
                **app._meta.handler_override_options[i][1]
            )


def handler_override(app: App) -> None:
    """
    This is a ``post_argument_parsing`` hook that overrides a configured
    handler if defined in ``App.Meta.handler_override_options`` and
    the option is passed at command line with a valid handler label.

    Args:
        app (instance): The application object.

    """
    if app._meta.handler_override_options is None:
        return

    for i in app._meta.handler_override_options.keys():
        if not hasattr(app.pargs, f'{i}_handler_override'):
            continue  # pragma: nocover
        elif getattr(app.pargs, f'{i}_handler_override') is None:
            continue  # pragma: nocover
        else:
            # get the argument value from command line
            argument = getattr(app.pargs, f'{i}_handler_override')
            setattr(app._meta, f'{i}_handler', argument)

            # and then re-setup the handler
            getattr(app, f'_setup_{i}_handler')()


def cement_signal_handler(signum: int, frame: Optional[FrameType]) -> Any:
    """
    Catch a signal, run the ``signal`` hook, and then raise an exception
    allowing the app to handle logic elsewhere.

    Args:
        signum (int): The signal number
        frame: The signal frame

    Raises:
        cement.core.exc.CaughtSignal: Raised, passing ``signum``, and ``frame``

    """
    LOG.debug(f'Caught signal {signum}')

    # FIXME: Maybe this isn't ideal... purhaps make
    # App.Meta.signal_handler a decorator that take the app object
    # and wraps/returns the actually signal handler?
    if frame:
        for f_global in frame.f_globals.values():
            if isinstance(f_global, App):
                app = f_global
                for res in app.hook.run('signal', app, signum, frame):
                    pass  # pragma: nocover
    raise exc.CaughtSignal(signum, frame)


class App(meta.MetaMixin):

    """The primary application object class."""

    class Meta:

        """
        Application meta-data (can also be passed as keyword arguments to the
        parent class).
        """

        label: str = None  # type: ignore
        """
        The name of the application.  This should be the common name as you
        would see and use at the command line.  For example ``helloworld``, or
        ``my-awesome-app``.
        """

        debug = False
        """
        This is set to ``True`` if any of the ``debug_argument_options``
        are passed at command line. Useful for debugging."""

        debug_argument_options = ['-d', '--debug']
        """
        The argument option(s) to toggle debug mode via cli. Set to `None` to
        remove these options from the app.
        """

        debug_argument_help = 'full application debug mode'
        """
        The debug argument help text that is displayed in ``--help``.
        """

        quiet = False
        """
        Suppress all console output (print/log/render). This is set to
        ``True`` if any of the ``quiet_argument_options`` are passed at
        command line."""

        quiet_argument_options = ['-q', '--quiet']
        """
        The argument option(s) to toggle quiet mode via cli. Set to `None` to
        remove these options from the app.
        """

        quiet_argument_help = 'suppress all console output'
        """
        The quiet argument help text that is displayed in ``--help``.
        """

        exit_on_close = False
        """
        Whether or not to call ``sys.exit()`` when ``close()`` is called.
        The default is ``False``, however if ``True`` then the app will call
        ``sys.exit(X)`` where ``X`` is ``self.exit_code``.
        """

        config_file_suffix = '.conf'
        """
        Extension used to identify application and plugin configuration files.
        """

        config_files: list[str] = None  # type: ignore
        """
        List of config files to parse (appended to the builtin list of config
        files defined by Cement).

        Note: Though ``App.Meta.config_files`` defaults to ``None``, Cement
        will set this to a default list based on ``App.Meta.label`` (or in
        other words, the name of the application).  This will equate to:

        .. code-block:: python

            [
                '/etc/myapp/myapp.conf',
                '~/.config/myapp/myapp.conf',
                '~/.myapp.conf',
            ]


        Files are loaded in order, and have precedence in order.  Therefore,
        the last configuration loaded has precedence (and overwrites settings
        loaded from previous configuration files).

        Note that ``.conf`` is the default config file extension, defined by
        ``App.Meta.config_file_suffix``.
        """

        config_dirs: list[str] = None  # type: ignore
        """
        List of config directories to search config files (appended to the
        builtin list of directories defined by Cement). For each directory
        cement will load all files that ends with ``.conf``. Note: Though
        ``App.Meta.config_dirs`` defaults to ``None``, Cement
        will set this to a default list based on ``App.Meta.label`` (or in
        other words, the name of the application).  This will equate to:

        .. code-block:: python

            [
                '/etc/myapp/ext.d/',
                '/etc/myapp/plugins.d/',
                '~/.myapp/config/ext.d/',
                '~/.myapp/config/plugins.d/',
            ]

        Directories and files inside are loaded in order, and have precedence
        in order.  Therefore, the last configuration loaded has precedence
        (and overwrites settings loaded from previous configuration files).
        These configuration will be overriden by configuration from
        ``CementApp.Meta.config_files``.

        Note that ``.conf`` is the default config file extension, defined by
        ``CementApp.Meta.config_file_suffix``.
        """

        plugins: list[str] = []
        """
        A list of plugins to load.  This is generally considered bad practice
        since plugins should be dynamically enabled/disabled via a plugin
        config file.
        """

        plugin_module: str = None  # type: ignore
        """
        A python package (dotted import path) where plugin code can be
        loaded from.  This is generally something like ``myapp.plugins``
        where a plugin file would live at ``myapp/plugins/myplugin.py`` or
        ``myapp/plugins/myplugin/`` (directory). This provides a facility for
        applications that have builtin plugins that ship with the applications
        source code and live in the same Python module.

        Note: Though the meta default is ``None``, Cement will set this to
        ``<app_label>.plugins`` if not set.
        """

        plugin_dirs: list[str] = None  # type: ignore
        """
        A list of directory paths where plugin code (modules) can be loaded
        from (appended to the builtin list of directories defined by Cement).

        Note: Though ``App.Meta.plugin_dirs`` defaults to ``None``, Cement will
        populate this with a default list based on ``App.Meta.label``.
        This will equate to:

        .. code-block:: python

            [
                '~/.myapp/plugins',
                '~/.config/myapp/plugins',
                '/usr/lib/myapp/plugins',
            ]


        Modules are attempted to be loaded in order, and will stop loading
        once a plugin is successfully loaded from a directory.  Therefore
        this is the oposite of configuration file loading, in that here the
        first has precedence.
        """

        plugin_dir: Optional[str] = None
        """
        A directory path where plugin code (modules) can be loaded from.
        By default, this setting is also overridden by the
        ``myapp.plugin_dir`` config setting parsed in any of the
        application configuration files.

        If set, this item will be **prepended** to ``Meta.plugin_dirs`` so
        that a users defined ``plugin_dir`` has precedence over others.

        In general, this setting should not be defined by the developer, as it
        is primarily used to allow the end-user to define a
        ``plugin_dir`` without completely trumping the hard-coded list
        of default ``plugin_dirs`` defined by the app/developer.
        """

        argv: list[str] = None  # type: ignore
        """
        A list of arguments to use for parsing command line arguments
        and options.

        Note: Though ``App.Meta.argv`` defaults to ``None``, Cement will set
        this to ``list(sys.argv[1:])`` if no argv is set in Meta during
        ``setup()``.
        """

        _choo_type = Dict[str, ArgparseArgumentType]
        core_handler_override_options: _choo_type = dict(
            output=(['-o'], dict(help='output handler')),
        )
        """
        Similar to ``App.Meta.handler_override_options`` but these are
        the core defaults required by Cement.  This dictionary can be
        overridden by ``App.Meta.handler_override_options`` (when they
        are merged together).
        """

        handler_override_options: Dict[str, ArgparseArgumentType] = {}
        """
        Dictionary of handler override options that will be added to the
        argument parser, and allow the end-user to override handlers.  Useful
        for interfaces that have multiple uses within the same application
        (for example: Output Handler (json, yaml, etc) or maybe a Cloud
        Provider Handler (rackspace, digitalocean, amazon, etc).

        This dictionary will merge with
        ``App.Meta.core_handler_override_options`` but this one has
        precedence.

        Dictionary Format:

        .. code-block:: text

            <interface_name> = (option_arguments, help_text)


        See ``App.Meta.core_handler_override_options`` for an example
        of what this should look like.

        Note, if set to ``None`` then no options will be defined, and the
        ``App.Meta.core_meta_override_options`` will be ignore (not
        recommended as some extensions rely on this feature).
        """

        config_section: str = None  # type: ignore
        """
        The base configuration section for the application.

        Note: Though ``App.Meta.config_section`` defaults to ``None``, Cement
        will set this to the value of ``App.Meta.label`` (or in other words,
        the name of the application).
        """

        config_defaults: Dict[str, Any] = None  # type: ignore
        """Default configuration dictionary.  Must be of type ``dict``."""

        meta_defaults: Dict[str, Any] = {}
        """
        Default meta-data dictionary used to pass high level options from the
        application down to handlers at the point they are registered by the
        framework **if the handler has not already been instantiated**.

        For example, if requiring the ``json`` extension, you might want to
        override ``JsonOutputHandler.Meta.json_module`` with ``ujson`` by
        doing the following:

        .. code-block:: python

            from cement import App

            META = {
                'output.json': {
                    'json_module': 'ujson',
                }
            }

            class MyApp(App):
                class Meta:
                    label = 'myapp'
                    extensions = ['json']
                    meta_defaults = META

        """

        catch_signals = SIGNALS
        """
        List of signals to catch, and raise ``cement.core.exc.CaughtSignal``
        for.  Can be set to ``None`` to disable signal handling.
        """

        signal_handler: Callable = cement_signal_handler
        """A function that is called to handle any caught signals."""

        config_handler = 'configparser'
        """
        A handler class that implements the Config interface.
        """

        mail_handler = 'dummy'
        """
        A handler class that implements the Mail interface.
        """

        extension_handler = 'cement'
        """
        A handler class that implements the Extension interface.
        """

        log_handler = 'logging'
        """
        A handler class that implements the Log interface.
        """

        plugin_handler = 'cement'
        """
        A handler class that implements the Plugin interface.
        """

        argument_handler = 'argparse'
        """
        A handler class that implements the Argument interface.
        """

        output_handler = 'dummy'
        """
        A handler class that implements the Output interface.
        """

        template_handler = 'dummy'
        """
        A handler class that implements the Template interface.
        """

        cache_handler: Optional[str] = None
        """
        A handler class that implements the Cache interface.
        """

        extensions: List[str] = []
        """List of additional framework extensions to load."""

        bootstrap: Optional[str] = None
        """
        A bootstrapping module to load after app creation, and before
        ``app.setup()`` is called.  This is useful for larger applications
        that need to offload their bootstrapping code such as registering
        hooks/handlers/etc to another file.

        This must be a dotted python module path.
        I.e. ``myapp.bootstrap`` (``myapp/bootstrap.py``).  Cement will then
        import the module, and if the module has a ``load()`` function, that
        will also be called.  Essentially, this is the same as an
        extension or plugin, but as a facility for the application itself
        to bootstrap hard-coded application code.  It is also called
        before plugins are loaded.
        """

        core_extensions = [
            'cement.ext.ext_dummy',
            'cement.ext.ext_smtp',
            'cement.ext.ext_plugin',
            'cement.ext.ext_configparser',
            'cement.ext.ext_logging',
            'cement.ext.ext_argparse',
        ]
        """
        List of Cement core extensions.  These are generally required by
        Cement and should only be modified if you know what you're
        doing.  Use ``App.Meta.extensions`` to add to this list, rather than
        overriding core extensions.  That said if you want to prune down
        your application, you can remove core extensions if they are
        not necessary (for example if using your own log handler
        extension you might not need/want ``LoggingLogHandler`` to be
        registered).
        """

        core_meta_override = [
            'debug',
            # 'plugin_config_dir',
            'plugin_dir',
            'ignore_deprecation_warnings',
            'template_dir',
            'mail_handler',
            'cache_handler',
            'log_handler',
            'output_handler',
            'template_handler',
        ]
        """
        List of meta options that can/will be overridden by config options
        of the ``base`` config section (where ``base`` is the base
        configuration section of the application which is determined by
        ``App.Meta.config_section`` but defaults to ``App.Meta.label``). These
        overrides are required by the framework to function properly and should
        not be used by end-user (developers) unless you really know what
        you're doing.  To add your own extended meta overrides you should use
        ``App.Meta.meta_override``.
        """

        meta_override: List[str] = []
        """
        List of meta options that can/will be overridden by config options
        of the ``base`` config section (where ``base`` is the
        base configuration section of the application which is determined
        by ``App.Meta.config_section`` but defaults to ``App.Meta.label``).
        """

        ignore_deprecation_warnings = False
        """Disable deprecation warnings from being logged by Cement."""

        template_module: Optional[str] = None
        """
        A python package (dotted import path) where template files can be
        loaded from.  This is generally something like ``myapp.templates``
        where a plugin file would live at ``myapp/templates/mytemplate.txt``.
        Templates are first loaded from ``App.Meta.template_dirs``, and
        and secondly from ``App.Meta.template_module``.  The
        ``template_dirs`` setting has presedence.
        """

        template_dirs: List[str] = None  # type: ignore
        """
        A list of directory paths where template files can be loaded
        from (appended to the builtin list of directories defined by Cement).

        Note: Though ``App.Meta.template_dirs`` defaults to ``None``,
        Cement will populate this with a default list based on
        ``App.Meta.label``.  This will equate to:

        .. code-block:: python

            [
                '~/.myapp/templates',
                '~/.config/myapp/templates',
                '/usr/lib/myapp/templates',
            ]


        Templates are attempted to be loaded in order, and will stop loading
        once a template is successfully loaded from a directory.
        """

        template_dir: Optional[str] = None
        """
        A directory path where template files can be loaded from.  By default,
        this setting is also overridden by the
        ``myapp.template_dir`` config setting parsed in any of the
        application configuration files .

        If set, this item will be **prepended** to
        ``App.Meta.template_dirs`` (giving it precedence over other
        ``template_dirs``.
        """

        framework_logging = True
        """
        This setting is deprecated and will be changed or removed in Cement
        v3.2.0. See:
        https://docs.builtoncement.com/release-information/deprecations#3.0.8-2

        Whether or not to enable Cement framework logging if ``--debug`` is
        passed at the command line.  This is separate from the application
        log, and is generally used for debugging issues with the framework
        and/or extensions primarily in development.

        This option is overridden by the environment variable
        `CEMENT_LOG`.  Therefore, if in production you do not
        want the Cement framework log enabled (when the ``debug`` option is
        passed at command line), you can set this option to ``False``. Setting
        ``CEMENT_LOG=1`` in the environment will trigger this setting to
        ``True``.
        """

        define_hooks: List[str] = []
        """
        List of hook definitions (labels).  Will be passed to
        ``self.hook.define(<hook_label>)``.  Must be a list of strings.

        I.e. ``['my_custom_hook', 'some_other_hook']``
        """

        hooks: List[Tuple[str, Callable]] = []
        """
        List of hooks to register when the app is created.  Will be passed to
        ``self.hook.register(<hook_label>, <hook_func>)``.  Must be a list of
        tuples in the form of ``(<hook_label>, <hook_func>)``.

        I.e. ``[('post_argument_parsing', my_hook_func)]``.
        """

        core_interfaces: List[Type[Interface]] = [
            extension.ExtensionInterface,
            log.LogInterface,
            config.ConfigInterface,
            mail.MailInterface,
            plugin.PluginInterface,
            output.OutputInterface,
            template.TemplateInterface,
            arg.ArgumentInterface,
            controller.ControllerInterface,
            cache.CacheInterface,
        ]
        """
        List of core interfaces to be defined (by the framework).  You should
        not modify this unless you really know what you're doing... instead,
        you probably want to add your own interfaces to
        ``App.Meta.interfaces``.
        """

        interfaces: List[Type[Interface]] = []
        """
        List of interfaces to be defined.  Must be a list of
        uninstantiated interface base classes.

        I.e. ``[MyCustomInterface, SomeOtherInterface]``
        """

        handlers: List[Type[Handler]] = []
        """
        List of handler classes to register.  Will be passed to
        ``handler.register(<handler_class>)``.  Must be a list of
        uninstantiated handler classes.

        I.e. ``[MyCustomHandler, SomeOtherHandler]``
        """

        alternative_module_mapping: Dict[str, str] = {}
        """
        EXPERIMENTAL FEATURE: This is an experimental feature added in Cement
        2.9.x and may or may not be removed in future versions of Cement.

        Dictionary of alternative, **drop-in** replacement modules to use
        selectively throughout the application, framework, or
        extensions.  Developers can optionally use the
        ``App.__import__()`` method to import simple modules, and if
        that module exists in this mapping it will import the alternative
        library in its place.

        This is a low-level feature and may not produce the results you are
        expecting.  Its purpose is to allow the developer to replace specific
        modules at a high level.  Example: For an application wanting to use
        ``ujson`` in place of ``json``, the developer could set the following:

        .. code-block:: python

            alternative_module_mapping = {
                'json' : 'ujson',
            }

        In the app, you would then load ``json`` as:

        .. code-block:: python

            _json = app.__import__('json')
            _json.dumps(data)


        Obviously, the replacement module **must be** a drop-in replace and
        function the same.
        """

        core_system_config_dirs = [
            join('/', 'etc', '{label}', 'ext.d'),
            join('/', 'etc', '{label}', 'plugins.d'),
        ]
        """
        List of builtin system level configuration directories to scan for
        config files.
        """

        core_user_config_dirs = [
            join('{home_dir}', '.config', '{label}', 'ext.d'),
            join('{home_dir}', '.config', '{label}', 'plugins.d'),
            join('{home_dir}', '.{label}', 'config', 'ext.d'),
            join('{home_dir}', '.{label}', 'config', 'plugins.d'),
        ]
        """
        List of builtin user level configuration directories to scan for
        config files.
        """

        core_system_config_files = [
            join('/', 'etc', '{label}', '{label}{suffix}'),
        ]
        """
        List of builtin system level configuration files.
        """

        core_user_config_files = [
            join('{home_dir}', '.config', '{label}', '{label}{suffix}'),
            join('{home_dir}', '.{label}', 'config', '{label}{suffix}'),
            join('{home_dir}', '.{label}{suffix}'),
        ]
        """
        List of builtin user level configuration files.
        """

        core_system_template_dirs = [
            '/usr/lib/{label}/templates',
        ]
        """
        List of builtin system level directories to scan for templates.
        """

        core_user_template_dirs = [
            join('{home_dir}', '.config', '{label}', 'templates'),
            join('{home_dir}', '.{label}', 'templates'),
        ]
        """
        List of builtin user level template directories to scan for templates.
        """

        core_system_plugin_dirs = [
            '/usr/lib/{label}/plugins',
        ]
        """
        List of builtin system level directories to scan for plugins.
        """

        core_user_plugin_dirs = [
            join('{home_dir}', '.config', '{label}', 'plugins'),
            join('{home_dir}', '.{label}', 'plugins'),
        ]
        """
        List of builtin user level directories to scan for plugins.
        """

    _meta: Meta  # type: ignore

    def __init__(self, label: Optional[str] = None, **kw: Any) -> None:
        super(App, self).__init__(**kw)

        # enable framework logging from environment?
        if 'CEMENT_LOG' in os.environ.keys():
            val = os.environ.get('CEMENT_LOG')
            assert val in ['0', '1'], \
                f'Invalid value for CEMENT_LOG ({val}). Must be one of: 0, 1'
            if is_true(val):
                self._meta.framework_logging = True
            else:
                self._meta.framework_logging = False

        if 'CEMENT_FRAMEWORK_LOGGING' in os.environ.keys():
            deprecate('3.0.8-1')
            val = os.environ.get('CEMENT_FRAMEWORK_LOGGING')
            assert val in ['0', '1'], (
                f'Invalid value for CEMENT_FRAMEWORK_LOGGING ({val}). Must '
                f'be one of: 0, 1'
            )
            if is_true(val):
                self._meta.framework_logging = True
            else:
                self._meta.framework_logging = False

        # DEPRECATE: in v3.2.0, this needs to set os.environ if is True
        if self._meta.framework_logging is True:
            deprecate('3.0.8-2')
            os.environ['CEMENT_LOG_DEPRECATED_DEBUG_OPTION'] = '1'

        # for convenience we translate this to _meta
        if label:
            self._meta.label = label

        self._validate_label()
        self._loaded_bootstrap = None
        self._parsed_args: Any = None
        self._last_rendered: Optional[Tuple[Any, Optional[str]]] = None
        self._extended_members: List[str] = []
        self.__saved_stdout__: TextIO = None  # type: ignore
        self.__saved_stderr__: TextIO = None  # type: ignore
        self.__retry_hooks__: List[Tuple[str, Callable]] = []
        self.handler: HandlerManager = None  # type: ignore
        self.interface: InterfaceManager = None  # type: ignore
        self.hook: HookManager = None  # type: ignore
        self.exit_code = 0
        self.ext: extension.ExtensionHandler = None  # type: ignore
        self.config: config.ConfigHandler = None  # type: ignore
        self.log: log.LogHandler = None  # type: ignore
        self.plugin: plugin.PluginHandler = None  # type: ignore
        self.args: arg.ArgumentHandler = None  # type: ignore
        self.output: output.OutputHandler = None  # type: ignore
        self.controller: controller.ControllerHandler = None  # type: ignore
        self.cache: cache.CacheHandler = None  # type: ignore
        self.mail: mail.MailHandler = None  # type: ignore

        # setup argv... this has to happen before lay_cement()
        if self._meta.argv is None:
            self._meta.argv = list(sys.argv[1:])

        # hack for command line debug/quiet options
        if self._meta.debug_argument_options is not None:
            if any(x in self.argv for x in self._meta.debug_argument_options):
                self._meta.debug = True

        if self._meta.quiet_argument_options is not None:
            if any(x in self.argv for x in self._meta.quiet_argument_options):
                self._meta.quiet = True
                self._suppress_output()

        self._lay_cement()

        # add deprecation warnings?
        # if is_true(os.environ.get('CEMENT_DEPRECATION_WARNINGS', 0)):
        #     self.hook.register('pre_close', display_deprecation_warnings)

    @property
    def label(self) -> str:
        return self._meta.label

    @property
    def debug(self) -> bool:
        """
        Application debug mode.

        :returns: boolean
        """
        return self._meta.debug

    @property
    def quiet(self) -> bool:
        """
        Application quiet mode.

        :returns: boolean
        """
        return self._meta.quiet

    @property
    def argv(self) -> List[str]:
        """The arguments list that will be used when self.run() is called."""
        return self._meta.argv

    def extend(self, member_name: str, member_object: Any) -> None:
        """
        Extend the ``App()`` object with additional functions/classes such
        as ``app.my_custom_function()``, etc.  It provides an interface for
        extensions to provide functionality that travel along with the
        application object.

        Args:
            member_name (str): The name to attach the object to.
            member_object: The function or class object to attach to
            ``App()``.

        Raises:
            cement.core.exc.FrameworkError: If ``App().member_name`` already
                exists.

        """
        if hasattr(self, member_name):
            raise exc.FrameworkError(f"App member '{member_name}' already exists!")
        LOG.debug(f"extending appication with '.{member_name}' ({member_object})")
        setattr(self, member_name, member_object)
        if member_name not in self._extended_members:
            self._extended_members.append(member_name)

    def _validate_label(self) -> None:
        if not self._meta.label:
            raise exc.FrameworkError("Application name missing.")

        # validate the name is ok
        ok = ['_', '-']
        for char in self._meta.label:
            if char in ok:
                continue

            if not char.isalnum():
                raise exc.FrameworkError(
                    "App label can only contain alpha-numeric, dashes, " +
                    "or underscores."
                )

    def setup(self) -> None:
        """
        This function wraps all ``_setup`` actons in one call.  It is called
        before ``self.run()``, allowing the application to be setup but not
        executed (possibly letting the developer perform other actions
        before full execution).

        All handlers should be instantiated and callable after setup is
        complete.

        """
        LOG.debug(f"now setting up the '{self._meta.label}' application")

        if self._meta.bootstrap is not None:
            LOG.debug(f"importing bootstrap code from {self._meta.bootstrap}")

            if self._meta.bootstrap not in sys.modules or self._loaded_bootstrap is None:
                __import__(self._meta.bootstrap, globals(), locals(), [], 0)
                if hasattr(sys.modules[self._meta.bootstrap], 'load'):
                    sys.modules[self._meta.bootstrap].load(self)

                self._loaded_bootstrap = sys.modules[self._meta.bootstrap]  # type: ignore
            else:
                reload_module(self._loaded_bootstrap)

        for res in self.hook.run('pre_setup', self):
            pass

        self._setup_extension_handler()
        self._setup_signals()
        self._setup_config_handler()
        self._setup_mail_handler()
        self._setup_cache_handler()
        self._setup_log_handler()
        self._setup_plugin_handler()
        self._setup_arg_handler()
        self._setup_output_handler()
        self._setup_template_handler()
        self._setup_controllers()

        for hook_spec in self.__retry_hooks__:
            self.hook.register(*hook_spec)

        for res in self.hook.run('post_setup', self):
            pass

    def run(self) -> Union[None, Any]:
        """
        This function wraps everything together (after ``self._setup()`` is
        called) to run the application.

        Returns:
            unknown: The result of the executed controller function if
            a base controller is set and a controller function is called,
            otherwise ``None`` if no controller dispatched or no controller
            function was called.

        """
        return_val = None

        LOG.debug('running pre_run hook')
        for res in self.hook.run('pre_run', self):
            pass

        # If controller exists, then dispatch it
        if self.controller:
            return_val = self.controller._dispatch()
        else:
            self._parse_args()  # pragma: nocover

        LOG.debug('running post_run hook')
        for res in self.hook.run('post_run', self):
            pass

        return return_val

    def run_forever(self, interval: int = 1, tb: bool = True) -> None:
        """
        This function wraps ``self.run()`` with an endless while loop.  If any
        exception is encountered it will be logged and then the application
        will be reloaded.

        Args:
            interval (int): The number of seconds to sleep before reloading the
                the appliction.
            tb (bool): Whether or not to print traceback if exception occurs.

        """

        if tb is True:
            import traceback

        while True:
            LOG.debug('inside run_forever() eternal loop')
            try:
                self.run()
            except Exception as e:
                self.log.fatal(f'Caught Exception: {e}')

                if tb is True:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    traceback.print_exception(
                        exc_type, exc_value, exc_traceback, limit=2,
                        file=sys.stdout
                    )
            sleep(interval)
            self.reload()

    def reload(self) -> None:
        """
        This function is useful for reloading a running applications, for
        example to reload configuration settings, etc.
        """
        LOG.debug(f'reloading the {self._meta.label} application')
        self._unlay_cement()
        self._lay_cement()
        self.setup()

    def _unlay_cement(self) -> None:
        for member in self._extended_members:
            delattr(self, member)
        self._extended_members = []
        self.handler.__handlers__ = {}
        self.hook.__hooks__ = {}

    def close(self, code: Optional[int] = None) -> None:
        """
        Close the application.  This runs the ``pre_close`` and ``post_close``
        hooks allowing plugins/extensions/etc to cleanup at the end of
        program execution.

        Args:
            code: An exit code to exit with (``int``), if ``None`` is
            passed then exit with whatever ``self.exit_code`` is currently set
            to.  Note: ``sys.exit()`` will only be called if
            ``App.Meta.exit_on_close==True``.
        """
        for res in self.hook.run('pre_close', self):
            pass

        LOG.debug(f"closing the {self._meta.label} application")

        # reattach our stdout if in quiet mode to avoid lingering file handles
        # resolves: https://github.com/datafolklabs/cement/issues/653
        if self._meta.quiet is True:
            self._unsuppress_output()

        # in theory, this should happen last-last... but at that point `self`
        # would be kind of busted after _unlay_cement() is run.
        for res in self.hook.run('post_close', self):
            pass

        self._unlay_cement()

        if code is not None:
            assert type(code) is int, \
                "Invalid exit status code (must be integer)"
            self.exit_code = code

        if self._meta.exit_on_close is True:
            sys.exit(self.exit_code)

    def render(self, data: Any,
               template: Optional[str] = None,
               out: IO = sys.stdout,
               handler: Optional[str] = None,
               **kw: Any) -> str:
        """
        This is a simple wrapper around ``self.output.render()`` which simply
        returns an empty string if no output handler is defined.

        Args:
            data (dict): The data dictionary to render.

        Keyword Args:
            template (str): The template to render to (note that some
                output handlers do not use templates).
            out: A file like object (i.e. ``sys.stdout``, or actual file).
                Set to ``None`` if no output is desired (just render and
                return). Default is ``sys.stdout``, however if ``App.quiet``
                is ``True``, this will be set to ``None``.
            handler: The output handler to use to render.  Defaults to
                ``App.Meta.output_handler``.

        Other Parameters:
            kw (dict): Additional keyword arguments will be passed to the
                output handler when calling ``self.output.render()``.

        """
        for res in self.hook.run('pre_render', self, data):
            if type(res) is not dict:
                LOG.debug("pre_render hook did not return a dict().")
            else:
                data = res

        # Issue #636: override sys.stdout if in quiet mode
        stdouts = [sys.stdout, self.__saved_stdout__]
        if self._meta.quiet is True and out in stdouts:
            out = None  # type: ignore

        kw['template'] = template

        if handler is not None:
            oh = self.handler.resolve('output', handler)
            oh._setup(self)  # type: ignore
        else:
            oh = self.output

        if oh is None:
            LOG.debug('render() called, but no output handler defined.')
            out_text = ''
        else:
            out_text = oh.render(data, **kw)

        for res in self.hook.run('post_render', self, out_text):
            if type(res) is not str:
                LOG.debug('post_render hook did not return a str()')
            else:
                out_text = str(res)

        if out is not None and not hasattr(out, 'write'):
            raise TypeError("Argument 'out' must be a 'file' like object")
        elif out is not None and out_text is None:
            LOG.debug('render() called but output text is None')
        elif out:
            out.write(out_text)

        self._last_rendered = (data, out_text)
        return out_text

    @property
    def last_rendered(self) -> Optional[Tuple[Dict[str, Any], Optional[str]]]:
        """
        Return the ``(data, output_text)`` tuple of the last time
        ``self.render()`` was called.

        Returns:
            tuple: ``(data, output_text)``

        """
        return self._last_rendered

    @property
    def pargs(self) -> Any:
        """
        Returns the ``parsed_args`` object as returned by
        ``self.args.parse()``.
        """
        return self._parsed_args

    def add_arg(self, *args: Any, **kw: Any) -> None:
        """A shortcut for ``self.args.add_argument``."""
        self.args.add_argument(*args, **kw)

    def _suppress_output(self) -> None:
        if self._meta.debug is True:
            LOG.debug('not suppressing console output because of debug mode')
            return

        LOG.debug('suppressing all console output')
        self.__saved_stdout__ = sys.stdout
        self.__saved_stderr__ = sys.stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

        # have to resetup the log handler to suppress console output
        if self.log is not None:
            self._setup_log_handler()

    def _unsuppress_output(self) -> None:
        LOG.debug('unsuppressing all console output')

        # don't accidentally close the actual <stdout>/<stderr>
        if hasattr(sys.stdout, 'name') and sys.stdout.name != '<stdout>':
            sys.stdout.close()
        if hasattr(sys.stderr, 'name') and sys.stderr.name != '<stderr>':
            sys.stderr.close()
        sys.stdout = self.__saved_stdout__
        sys.stderr = self.__saved_stderr__

        # have to resetup the log handler to unsuppress console output
        if self.log is not None:
            self._setup_log_handler()

    def _lay_cement(self) -> None:
        """Initialize the framework."""
        LOG.debug(f"laying cement for the '{self._meta.label}' application")

        self.interface = InterfaceManager(self)
        self.handler = HandlerManager(self)
        self.hook = HookManager(self)

        # define framework hooks
        self.hook.define('pre_setup')
        self.hook.define('post_setup')
        self.hook.define('pre_run')
        self.hook.define('post_run')
        self.hook.define('pre_argument_parsing')
        self.hook.define('post_argument_parsing')
        self.hook.define('pre_close')
        self.hook.define('post_close')
        self.hook.define('signal')
        self.hook.define('pre_render')
        self.hook.define('post_render')

        # define application hooks from meta
        for label in self._meta.define_hooks:
            self.hook.define(label)

        # register some built-in framework hooks
        self.hook.register('post_setup', add_handler_override_options,
                           weight=-99)
        self.hook.register('post_argument_parsing',
                           handler_override, weight=-99)

        # register application hooks from meta.  the hooks listed in
        # App.Meta.hooks are registered here, so obviously can not be
        # for any hooks other than the builtin framework hooks that we just
        # defined here (above).  Anything that we couldn't register here
        # will be retried after setup
        self.__retry_hooks__ = []
        for hook_spec in self._meta.hooks:
            if not self.hook.defined(hook_spec[0]):
                LOG.debug(f'hook {hook_spec[0]} not defined, will retry after setup')
                self.__retry_hooks__.append(hook_spec)
            else:
                self.hook.register(*hook_spec)

        # define interfaces
        for i in self._meta.core_interfaces:
            self.interface.define(i)

        for i in self._meta.interfaces:
            self.interface.define(i)

        # extension handler is the only thing that can't be loaded... as,
        # well, an extension.  ;)
        self.handler.register(extension.ExtensionHandler)

        # register application handlers
        for handler_class in self._meta.handlers:
            self.handler.register(handler_class)

    def _parse_args(self) -> None:
        for res in self.hook.run('pre_argument_parsing', self):
            pass

        self._parsed_args = self.args.parse(self.argv)

        for res in self.hook.run('post_argument_parsing', self):
            pass

    def catch_signal(self, signum: int) -> None:
        """
        Add ``signum`` to the list of signals to catch and handle by Cement.

        Args:
            signum (int): The signal number to catch.  See Python
                :py:mod:`signal library <python:signal>`.
        """

        LOG.debug("adding signal handler %s for signal %s" % (
            self._meta.signal_handler, signum)
        )
        signal.signal(signum, self._meta.signal_handler)

    def _setup_signals(self) -> None:
        if self._meta.catch_signals is None:
            LOG.debug("catch_signals=None... not handling any signals")
            return

        for signum in self._meta.catch_signals:
            self.catch_signal(signum)

    def _resolve_handler(self,
                         handler_type: str,
                         handler_def: Union[str, Type[Handler], Handler],
                         raise_error: bool = True) -> Handler:
        # meta_defaults = {}
        # if type(handler_def) == str:
        #     _meta_label = "%s.%s" % (handler_type, handler_def)
        #     meta_defaults = self._meta.meta_defaults.get(_meta_label, {})
        # elif hasattr(handler_def, 'Meta'):
        #     _meta_label = "%s.%s" % (handler_type, handler_def.Meta.label)
        #     meta_defaults = self._meta.meta_defaults.get(_meta_label, {})

        han: Handler
        han = self.handler.resolve(handler_type,  # type: ignore
                                   handler_def,
                                   raise_error=raise_error,
                                   setup=True)
        return han

    def _setup_extension_handler(self) -> None:
        LOG.debug(f"setting up {self._meta.label}.extension handler")
        self.ext = self._resolve_handler('extension',  # type: ignore
                                         self._meta.extension_handler)
        self.ext.load_extensions(self._meta.core_extensions)
        self.ext.load_extensions(self._meta.extensions)

    def _find_config_files(self, path: str) -> List[str]:
        found_files = []
        if not os.path.isdir(path):
            return []
        files = os.listdir(path)
        files.sort()
        for f in files:
            if f.endswith(self._meta.config_file_suffix):
                found_files.append(fs.join(path, f))
        return found_files

    def _setup_config_handler(self) -> None:
        LOG.debug(f"setting up {self._meta.label}.config handler")
        label = self._meta.label
        ext = self._meta.config_file_suffix
        self.config = self._resolve_handler('config',  # type: ignore
                                            self._meta.config_handler)
        if self._meta.config_section is None:
            self._meta.config_section = label

        self.config.add_section(self._meta.config_section)

        if self._meta.config_defaults is not None:
            self.config.merge(self._meta.config_defaults)

        if self._meta.config_files is None:
            self._meta.config_files = []

        if self._meta.config_dirs is None:
            self._meta.config_dirs = []

        config_files = []
        config_dirs = []

        template_dict = {
            'label': self._meta.label,
            'suffix': ext,
            'home_dir': fs.HOME_DIR,
        }

        # generate a final list of directories based on precedence (user level
        # paths take precedence).

        for f in self._meta.core_system_config_files:
            f = f.format(**template_dict)
            if f not in config_files:
                config_files.append(f)

        for d in self._meta.core_system_config_dirs:
            d = d.format(**template_dict)
            if d not in config_dirs:
                config_dirs.append(d)
            for f in self._find_config_files(d):
                if f not in config_files:
                    config_files.append(f)

        for f in self._meta.config_files:
            f = f.format(**template_dict)
            if f not in config_files:
                config_files.append(f)

        for d in self._meta.config_dirs:
            d = d.format(**template_dict)
            if d not in config_dirs:
                config_dirs.append(d)
            for f in self._find_config_files(d):
                if f not in config_files:
                    config_files.append(f)

        for f in self._meta.core_user_config_files:
            f = f.format(**template_dict)
            if f not in config_files:
                config_files.append(f)

        for d in self._meta.core_user_config_dirs:
            d = d.format(**template_dict)
            if d not in config_dirs:
                config_dirs.append(d)
            for f in self._find_config_files(d):
                if f not in config_files:
                    config_files.append(f)

        # reset for final lists

        self._meta.config_files = []
        self._meta.config_dirs = []

        for d in config_dirs:
            self.add_config_dir(d)

        for f in config_files:
            self.add_config_file(f)
            self.config.parse_file(f)

        self.validate_config()

        # hack for debug command line option
        if self._meta.debug is True:
            self.config.set(self._meta.config_section, 'debug', True)

        # override select Meta via config
        base_dict = self.config.get_section_dict(self._meta.config_section)

        for key in base_dict:
            if key in self._meta.core_meta_override or \
                    key in self._meta.meta_override:
                # kind of a hack for core_meta_override
                if key in ['debug']:
                    setattr(self._meta, key, is_true(base_dict[key]))
                else:
                    setattr(self._meta, key, base_dict[key])

        # load extensions from configuraton file
        if 'extensions' in self.config.keys(self._meta.config_section):
            exts = self.config.get(label, 'extensions')

            # convert a comma-separated string to a list
            if type(exts) is str:
                ext_list = exts.split(',')

                # clean up extra space if they had it inbetween commas
                ext_list = [x.strip() for x in ext_list]

                # set the new extensions value in the config
                self.config.set(label, 'extensions', ext_list)

            # otherwise, if it's a list
            elif type(exts) is list:
                ext_list = exts

            for ext in ext_list:
                # load the extension
                self.ext.load_extension(ext)

                # add to meta data
                self._meta.extensions.append(ext)

    def _setup_mail_handler(self) -> None:
        LOG.debug(f"setting up {self._meta.label}.mail handler")
        self.mail = self._resolve_handler('mail',  # type: ignore
                                          self._meta.mail_handler)

    def _setup_log_handler(self) -> None:
        LOG.debug(f"setting up {self._meta.label}.log handler")
        self.log = self._resolve_handler('log', self._meta.log_handler)  # type: ignore

    def _setup_plugin_handler(self) -> None:
        LOG.debug(f"setting up {self._meta.label}.plugin handler")

        # plugin dirs
        if self._meta.plugin_dirs is None:
            self._meta.plugin_dirs = []

        plugin_dirs = []
        template_dict = {
            'label': self._meta.label,
            'home_dir': fs.HOME_DIR,
        }

        # generate a final list of directories based on precedence (user level
        # paths take precedence).

        for d in self._meta.core_system_plugin_dirs:
            d = d.format(**template_dict)
            if d not in plugin_dirs:
                plugin_dirs.append(d)

        for d in self._meta.plugin_dirs:
            d = d.format(**template_dict)
            if d not in plugin_dirs:
                plugin_dirs.append(d)

        if self._meta.plugin_dir is not None:
            d = self._meta.plugin_dir.format(**template_dict)
            plugin_dirs.append(d)

        for d in self._meta.core_user_plugin_dirs:
            d = d.format(**template_dict)
            if d not in plugin_dirs:
                plugin_dirs.append(d)

        # reset our final list

        self._meta.plugin_dirs = []

        # reverse it so that first found takes precedence
        plugin_dirs.reverse()

        for path in plugin_dirs:
            self.add_plugin_dir(path)

        # plugin bootstrap
        if self._meta.plugin_module is None:
            self._meta.plugin_module = f'{self._meta.label}.plugins'

        self.plugin = self._resolve_handler('plugin',  # type: ignore
                                            self._meta.plugin_handler)
        self.plugin.load_plugins(self._meta.plugins)
        self.plugin.load_plugins(self.plugin.get_enabled_plugins())

    def _setup_output_handler(self) -> None:
        if self._meta.output_handler is None:
            LOG.debug("no output handler defined, skipping.")
            return

        LOG.debug(f"setting up {self._meta.label}.output handler")
        self.output = self._resolve_handler('output',  # type: ignore
                                            self._meta.output_handler,
                                            raise_error=False)

    def _setup_template_handler(self) -> None:
        if self._meta.template_handler is None:
            LOG.debug("no template handler defined, skipping.")
            return

        label = self._meta.label
        LOG.debug(f"setting up {self._meta.label}.template handler")
        self.template = self._resolve_handler('template',
                                              self._meta.template_handler,
                                              raise_error=False)
        # template module
        if self._meta.template_module is None:
            self._meta.template_module = f'{label}.templates'

        # template dirs
        if self._meta.template_dirs is None:
            self._meta.template_dirs = []

        template_dirs = []
        template_dict = {
            'label': self._meta.label,
            'home_dir': fs.HOME_DIR,
        }

        # generate a final list of directories based on precedence (user level
        # paths take precedence).

        for d in self._meta.core_system_template_dirs:
            d = d.format(**template_dict)
            if d not in template_dirs:
                template_dirs.append(d)

        for d in self._meta.template_dirs:
            d = d.format(**template_dict)
            if d not in template_dirs:
                template_dirs.append(d)

        if self._meta.template_dir is not None:
            d = self._meta.template_dir.format(**template_dict)
            template_dirs.append(d)

        for d in self._meta.core_user_template_dirs:
            d = d.format(**template_dict)
            if d not in template_dirs:
                template_dirs.append(d)

        # reset final list
        self._meta.template_dirs = []

        # reverse so that first found has precedence
        template_dirs.reverse()

        for path in template_dirs:
            self.add_template_dir(path)

    def _setup_cache_handler(self) -> None:
        if self._meta.cache_handler is None:
            LOG.debug("no cache handler defined, skipping.")
            return

        LOG.debug(f"setting up {self._meta.label}.cache handler")
        self.cache = self._resolve_handler('cache',  # type: ignore
                                           self._meta.cache_handler,
                                           raise_error=False)

    def _setup_arg_handler(self) -> None:
        LOG.debug(f"setting up {self._meta.label}.arg handler")
        self.args = self._resolve_handler('argument',  # type: ignore
                                          self._meta.argument_handler)
        self.args.prog = self._meta.label

        if self._meta.debug_argument_options is not None:
            self.args.add_argument(*self._meta.debug_argument_options,
                                   dest='debug',
                                   action='store_true',
                                   help=self._meta.debug_argument_help)
        if self._meta.quiet_argument_options is not None:
            self.args.add_argument(*self._meta.quiet_argument_options,
                                   dest='suppress_output',
                                   action='store_true',
                                   help=self._meta.quiet_argument_help)

        # merge handler override meta data
        if self._meta.handler_override_options is not None:
            # merge the core handler override options with developer defined
            # options
            core = self._meta.core_handler_override_options.copy()
            dev = self._meta.handler_override_options.copy()
            core.update(dev)

            self._meta.handler_override_options = core

    def _setup_controllers(self) -> None:
        LOG.debug("setting up application controllers")

        if self.handler.registered('controller', 'base'):
            self.controller = self._resolve_handler('controller', 'base')  # type: ignore

        else:
            class DefaultBaseController(Controller):
                class Meta:
                    label = 'base'

                def _default(self) -> None:
                    # don't enforce anything cause developer might not be
                    # using controllers... if they are, they should define
                    # a base controller.
                    pass

            self.handler.register(DefaultBaseController)
            self.controller = self._resolve_handler('controller', 'base')  # type: ignore

    def validate_config(self) -> None:
        """
        Validate application config settings.

        Example:

        .. code-block:: python

            import os
            from cement import App

            class MyApp(App):
                class Meta:
                    label = 'myapp'

                def validate_config(self):
                    super(MyApp, self).validate_config()

                    # test that the log file directory exist, if not create it
                    logdir = os.path.dirname(self.config.get('log', 'file'))

                    if not os.path.exists(logdir):
                        os.makedirs(logdir)

        """
        pass

    def add_config_dir(self, path: str) -> None:
        """
        Append a directory ``path`` to the list of directories to parse for
        config files.

        Args:
            path (str): Directory path that contains config files.

        Example:

        .. code-block:: python

            app.add_config_dir('/path/to/my/config/')

        """
        path = fs.abspath(path)
        if path not in self._meta.config_dirs:
            self._meta.config_dirs.append(path)

    def add_config_file(self, path: str) -> None:
        """
        Append a file ``path`` to the list of configuration files to parse.

        Args:
            path (str): Configuration file path..

        Example:

        .. code-block:: python

            app.add_config_file('/path/to/my/config/file')

        """
        path = fs.abspath(path)
        if path not in self._meta.config_files:
            self._meta.config_files.append(path)

    def add_plugin_dir(self, path: str) -> None:
        """
        Append a directory ``path`` to the list of directories to scan for
        plugins.

        Args:
            path (str): Directory path that contains plugin files.

        Example:

        .. code-block:: python

            app.add_plugin_dir('/path/to/my/plugins')

        """
        path = fs.abspath(path)
        if path not in self._meta.plugin_dirs:
            self._meta.plugin_dirs.append(path)

    def add_template_dir(self, path: str) -> None:
        """
        Append a directory ``path`` to the list of template directories to
        parse for templates.

        Args:
            path (str): Directory path that contains template files.

        Example:

        .. code-block:: python

            app.add_template_dir('/path/to/my/templates')

        """
        path = fs.abspath(path)
        if path not in self._meta.template_dirs:
            self._meta.template_dirs.append(path)

    def remove_template_dir(self, path: str) -> None:
        """
        Remove a directory ``path`` from the list of template directories to
        parse for templates.

        Args:
            path (str): Directory path that contains template files.

        Example:

            .. code-block:: python

                app.remove_template_dir('/path/to/my/templates')

        """
        path = fs.abspath(path)
        if path in self._meta.template_dirs:
            self._meta.template_dirs.remove(path)

    def __import__(self, obj: Any, from_module: Optional[str] = None) -> ModuleType:
        # EXPERIMENTAL == UNDOCUMENTED
        mapping = self._meta.alternative_module_mapping

        if from_module is not None:
            _from = mapping.get(from_module, from_module)
            _loaded = __import__(_from, globals(), locals(), [obj], 0)
            return getattr(_loaded, obj)  # type: ignore
        else:
            obj = mapping.get(obj, obj)
            _loaded = __import__(obj, globals(), locals(), [], 0)

        return _loaded

    def __enter__(self) -> App:
        self.setup()
        return self

    def __exit__(self,
                 exc_type: type[BaseException] | None,
                 exc_value: BaseException | None,
                 exc_traceback: TracebackType | None) -> None:
        # only close the app if there are no unhandled exceptions
        if exc_type is None:
            self.close()


class TestApp(App):

    """
    App subclass useful for testing.

    """

    # tells pytest to not consider this a class for testing
    __test__ = False

    class Meta:
        label: str = f"app-{misc.rando()[:12]}"
        argv: List[str] = []
        core_system_config_files: List[str] = []
        core_user_config_files: List[str] = []
        config_files: List[str] = []
        core_system_config_dirs: List[str] = []
        core_user_config_dirs: List[str] = []
        config_dirs: List[str] = []
        core_system_template_dirs: List[str] = []
        core_user_template_dirs: List[str] = []
        core_system_plugin_dirs: List[str] = []
        core_user_plugin_dirs: List[str] = []
        plugin_dirs: List[str] = []
        exit_on_close: bool = False
