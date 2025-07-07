"""Cement core foundation module."""

import re
import os
import sys
import signal
from ..core import backend, exc, handler, hook, log, config, plugin, interface
from ..core import output, extension, arg, controller, meta, cache, mail
from ..utils.misc import is_true, minimal_logger
from ..utils import fs

if sys.version_info[0] >= 3:
    from importlib import reload  # pragma: nocover
    from io import StringIO  # pragma: nocover
else:
    from StringIO import StringIO  # pragma: nocover

LOG = minimal_logger(__name__)


class NullOut(object):

    def write(self, s):
        pass

    def flush(self):
        pass


def add_handler_override_options(app):
    """
    This is a ``post_setup`` hook that adds the handler override options to
    the argument parser

    :param app: The application object.

    """
    if app._meta.handler_override_options is None:
        return

    for i in app._meta.handler_override_options:
        if i not in interface.list():
            LOG.debug("interface '%s'" % i +
                      " is not defined, can not override handlers")
            continue

        if len(handler.list(i)) > 1:
            handlers = []
            for h in handler.list(i):
                handlers.append(h())

            choices = [x._meta.label
                       for x in handlers
                       if x._meta.overridable is True]

            # don't display the option if no handlers are overridable
            if not len(choices) > 0:
                LOG.debug("no handlers are overridable within the " +
                          "%s interface" % i)
                continue

            # override things that we need to control
            argument_kw = app._meta.handler_override_options[i][1]
            argument_kw['dest'] = '%s_handler_override' % i
            argument_kw['action'] = 'store'
            argument_kw['choices'] = choices

            app.args.add_argument(
                *app._meta.handler_override_options[i][0],
                **app._meta.handler_override_options[i][1]
            )


def handler_override(app):
    """
    This is a ``post_argument_parsing`` hook that overrides a configured
    handler if defined in ``CementApp.Meta.handler_override_options`` and
    the option is passed at command line with a valid handler label.

    :param app: The application object.

    """
    if app._meta.handler_override_options is None:
        return

    for i in app._meta.handler_override_options.keys():
        if not hasattr(app.pargs, '%s_handler_override' % i):
            continue
        elif getattr(app.pargs, '%s_handler_override' % i) is None:
            continue
        else:
            # get the argument value from command line
            argument = getattr(app.pargs, '%s_handler_override' % i)
            setattr(app._meta, '%s_handler' % i, argument)

            # and then re-setup the handler
            getattr(app, '_setup_%s_handler' % i)()


def cement_signal_handler(signum, frame):
    """
    Catch a signal, run the 'signal' hook, and then raise an exception
    allowing the app to handle logic elsewhere.

    :param signum: The signal number
    :param frame: The signal frame.
    :raises: cement.core.exc.CaughtSignal

    """
    LOG.debug('Caught signal %s' % signum)

    for res in hook.run('signal', signum, frame):
        pass

    raise exc.CaughtSignal(signum, frame)


class CementApp(meta.MetaMixin):

    """
    The primary class to build applications from.

    Usage:

    The following is the simplest CementApp:

    .. code-block:: python

        from cement.core.foundation import CementApp

        with CementApp('helloworld') as app:
            app.run()


    Alternatively, the above could be written as:

    .. code-block:: python

        from cement.core.foundation import CementApp

        app = foundation.CementApp('helloworld')
        app.setup()
        app.run()
        app.close()


    A more advanced example looks like:

    .. code-block:: python

        from cement.core.foundation import CementApp
        from cement.core.controller import CementBaseController, expose

        class MyController(CementBaseController):
            class Meta:
                label = 'base'
                arguments = [
                    ( ['-f', '--foo'], dict(help='Notorious foo option') ),
                    ]
                config_defaults = dict(
                    debug=False,
                    some_config_param='some_value',
                    )

            @expose(help='This is the default command', hide=True)
            def default(self):
                print('Hello World')

        class MyApp(CementApp):
            class Meta:
                label = 'helloworld'
                extensions = ['daemon','json',]
                base_controller = MyController

        with MyApp() as app:
            app.run()

    """
    class Meta:

        """
        Application meta-data (can also be passed as keyword arguments to the
        parent class).
        """

        label = None
        """
        The name of the application.  This should be the common name as you
        would see and use at the command line.  For example 'helloworld', or
        'my-awesome-app'.
        """

        debug = False
        """
        Used internally, and should not be used by developers.  This is set
        to `True` if `--debug` is passed at command line."""

        exit_on_close = True
        """
        Whether or not to call ``sys.exit()`` when ``close()`` is called.
        Generally only used for testing to avoid having to catch
        ``SystemExit`` three thousand times.
        """

        config_files = None
        """
        List of config files to parse.

        Note: Though Meta.config_section defaults to None, Cement will
        set this to a default list based on Meta.label (or in other words,
        the name of the application).  This will equate to:

        .. code-block:: python

            ['/etc/<app_label>/<app_label>.conf',
             '~/.<app_label>.conf',
             '~/.<app_label>/config']


        Files are loaded in order, and have precedence in order.  Therefore,
        the last configuration loaded has precedence (and overwrites settings
        loaded from previous configuration files).
        """

        plugins = []
        """
        A list of plugins to load.  This is generally considered bad
        practice since plugins should be dynamically enabled/disabled
        via a plugin config file.
        """

        plugin_config_dirs = None
        """
        A list of directory paths where plugin config files can be found.
        Files must end in `.conf` or they will be ignored.

        Note: Though ``CementApp.Meta.plugin_config_dirs`` is ``None``, Cement
        will set this to a default list based on ``CementApp.Meta.label``.
        This will equate to:

        .. code-block:: python

            ['/etc/<app_label>/plugins.d', '~/.<app_label>/plugin.d']


        Files are loaded in order, and have precedence in that order.
        Therefore, the last configuration loaded has precedence (and
        overwrites settings loaded from previous configuration files).
        """

        plugin_config_dir = None
        """
        A directory path where plugin config files can be found.  Files
        must end in `.conf`.  By default, this setting is also overridden
        by the ``[<app_label>] -> plugin_config_dir`` config setting parsed in
        any of the application configuration files.

        If set, this item will be **appended** to
        ``CementApp.Meta.plugin_config_dirs`` so that it's settings will have
        presedence over other configuration files.

        In general, this setting should not be defined by the developer, as it
        is primarily used to allow the end-user to define a
        ``plugin_config_dir`` without completely trumping the hard-coded list
        of default ``plugin_config_dirs`` defined by the app/developer.
        """

        plugin_bootstrap = None
        """
        A python package (dotted import path) where plugin code can be
        loaded from.  This is generally something like ``myapp.plugins``
        where a plugin file would live at ``myapp/plugins/myplugin.py``.
        This provides a facility for applications that have builtin plugins
        that ship with the applications source code and live in the same
        Python module.

        Note: Though the meta default is ``None``, Cement will set this to
        ``<app_label>.plugins`` if not set.
        """

        plugin_dirs = None
        """
        A list of directory paths where plugin code (modules) can be loaded
        from.

        Note: Though ``CementApp.Meta.plugin_dirs`` is None, Cement will set
        this to a default list based on ``CementApp.Meta.label`` if not set.
        This will equate to:

        .. code-block:: python

            ['~/.<app_label>/plugins', '/usr/lib/<app_label>/plugins']


        Modules are attempted to be loaded in order, and will stop loading
        once a plugin is successfully loaded from a directory.  Therefore
        this is the oposite of configuration file loading, in that here the
        first has precedence.
        """

        plugin_dir = None
        """
        A directory path where plugin code (modules) can be loaded from.
        By default, this setting is also overridden by the
        ``[<app_label>] -> plugin_dir`` config setting parsed in any of the
        application configuration files.

        If set, this item will be **prepended** to ``Meta.plugin_dirs`` so
        that a users defined ``plugin_dir`` has precedence over others.

        In general, this setting should not be defined by the developer, as it
        is primarily used to allow the end-user to define a
        ``plugin_dir`` without completely trumping the hard-coded list
        of default ``plugin_dirs`` defined by the app/developer.
        """

        argv = None
        """
        A list of arguments to use for parsing command line arguments
        and options.

        Note: Though Meta.argv defaults to None, Cement will set this to
        ``list(sys.argv[1:])`` if no argv is set in Meta during setup().
        """

        arguments_override_config = False
        """
        A boolean to toggle whether command line arguments should
        override configuration values if the argument name matches the
        config key.  I.e. --foo=bar would override config['myapp']['foo'].

        This is different from ``override_arguments`` in that if
        ``arguments_override_config`` is ``True``, then all arguments will
        override (you don't have to list them all).
        """

        override_arguments = ['debug']
        """
        List of arguments that override their configuration counter-part.
        For example, if ``--debug`` is passed (and it's config value is
        ``debug``) then the ``debug`` key of all configuration sections will
        be overridden by the value of the command line option (``True`` in
        this example).

        This is different from ``arguments_override_config`` in that this is
        a selective list of specific arguments to override the config with
        (and not all arguments that match the config).  This list will take
        affect whether ``arguments_override_config`` is ``True`` or ``False``.
        """

        core_handler_override_options = dict(
            output=(['-o'], dict(help='output handler')),
        )
        """
        Similar to ``CementApp.Meta.handler_override_options`` but these are
        the core defaults required by Cement.  This dictionary can be
        overridden by ``CementApp.Meta.handler_override_options`` (when they
        are merged together).
        """

        handler_override_options = {}
        """
        Dictionary of handler override options that will be added to the
        argument parser, and allow the end-user to override handlers.  Useful
        for interfaces that have multiple uses within the same application
        (for example: Output Handler (json, yaml, etc) or maybe a Cloud
        Provider Handler (rackspace, digitalocean, amazon, etc).

        This dictionary will merge with
        ``CementApp.Meta.core_handler_override_options`` but this one has
        precedence.

        Dictionary Format:

        .. code-block:: text

            <interface_name> = (option_arguments, help_text)


        See ``CementApp.Meta.core_handler_override_options`` for an example
        of what this should look like.

        Note, if set to ``None`` then no options will be defined, and the
        ``CementApp.Meta.core_meta_override_options`` will be ignore (not
        recommended as some extensions rely on this feature).
        """

        config_section = None
        """
        The base configuration section for the application.

        Note: Though Meta.config_section defaults to None, Cement will
        set this to the value of Meta.label (or in other words, the name
        of the application).
        """

        config_defaults = None
        """Default configuration dictionary.  Must be of type 'dict'."""

        catch_signals = [signal.SIGTERM, signal.SIGINT]
        """
        List of signals to catch, and raise exc.CaughtSignal for.
        Can be set to None to disable signal handling.
        """

        signal_handler = cement_signal_handler
        """A function that is called to handle any caught signals."""

        config_handler = 'configparser'
        """
        A handler class that implements the IConfig interface.
        """

        mail_handler = 'dummy'
        """
        A handler class that implements the IMail interface.
        """

        extension_handler = 'cement'
        """
        A handler class that implements the IExtension interface.
        """

        log_handler = 'logging'
        """
        A handler class that implements the ILog interface.
        """

        plugin_handler = 'cement'
        """
        A handler class that implements the IPlugin interface.
        """

        argument_handler = 'argparse'
        """
        A handler class that implements the IArgument interface.
        """

        output_handler = 'dummy'
        """
        A handler class that implements the IOutput interface.
        """

        cache_handler = None
        """
        A handler class that implements the ICache interface.
        """

        base_controller = None
        """
        This is the base application controller.  If a controller is set,
        runtime operations are passed to the controller for command
        dispatch and argument parsing when CementApp.run() is called.

        Note that cement will automatically set the `base_controller` to a
        registered controller whose label is 'base' (only if `base_controller`
        is not currently set).
        """

        extensions = []
        """List of additional framework extensions to load."""

        bootstrap = None
        """
        A bootstrapping module to load after app creation, and before
        app.setup() is called.  This is useful for larger applications
        that need to offload their bootstrapping code such as registering
        hooks/handlers/etc to another file.

        This must be a dotted python module path.
        I.e. 'myapp.bootstrap' (myapp/bootstrap.py).  Cement will then
        import the module, and if the module has a 'load()' function, that
        will also be called.  Essentially, this is the same as an
        extension or plugin, but as a facility for the application itself
        to bootstrap 'hardcoded' application code.  It is also called
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
        doing.  Use 'extensions' to add to this list, rather than
        overriding core extensions.  That said if you want to prune down
        your application, you can remove core extensions if they are
        not necessary (for example if using your own log handler
        extension you likely don't want/need LoggingLogHandler to be
        registered).
        """

        core_meta_override = [
            'debug',
            'plugin_config_dir',
            'plugin_dir',
            'ignore_deprecation_warnings',
            'template_dir',
            'cache_handler',
            'mail_handler',
        ]
        """
        List of meta options that can/will be overridden by config options
        of the '[base]' config section (where [base] is the base
        configuration section of the application which is determined by
        Meta.config_section but defaults to Meta.label). These overrides
        are required by the framework to function properly and should not
        be used by end user (developers) unless you really know what
        you're doing.  To add your own extended meta overrides please use
        'meta_override'.
        """

        meta_override = []
        """
        List of meta options that can/will be overridden by config options
        of the '[base]' config section (where [base] is the
        base configuration section of the application which is determined
        by Meta.config_section but defaults to Meta.label).
        """

        ignore_deprecation_warnings = False
        """Disable deprecation warnings from being logged by Cement."""

        template_module = None
        """
        A python package (dotted import path) where template files can be
        loaded from.  This is generally something like ``myapp.templates``
        where a plugin file would live at ``myapp/templates/mytemplate.txt``.
        Templates are first loaded from ``CementApp.Meta.template_dirs``, and
        and secondly from ``CementApp.Meta.template_module``.  The
        ``template_dirs`` setting has presedence.
        """

        template_dirs = None
        """
        A list of directory paths where template files can be loaded
        from.

        Note: Though ``CementApp.Meta.template_dirs`` defaults to ``None``,
        Cement will set this to a default list based on
        ``CementApp.Meta.label``.  This will equate to:

        .. code-block:: python

            ['~/.<app_label>/templates', '/usr/lib/<app_label>/templates']


        Templates are attempted to be loaded in order, and will stop loading
        once a template is successfully loaded from a directory.
        """

        template_dir = None
        """
        A directory path where template files can be loaded from.  By default,
        this setting is also overridden by the
        ``[<app_label>] -> template_dir`` config setting parsed in any of the
        application configuration files .

        If set, this item will be **prepended** to
        ``CementApp.Meta.template_dirs`` (giving it precedence over other
        ``template_dirs``.
        """

        framework_logging = True
        """
        Whether or not to enable Cement framework logging.  This is separate
        from the application log, and is generally used for debugging issues
        with the framework and/or extensions primarily in development.

        This option is overridden by the environment variable
        `CEMENT_FRAMEWORK_LOGGING`.  Therefore, if in production you do not
        want the Cement framework log enabled, you can set this option to
        ``False`` but override it in your environment by doing something like
        ``export CEMENT_FRAMEWORK_LOGGING=1`` in your shell whenever you need
        it enabled.
        """

        define_hooks = []
        """
        List of hook definitions (label).  Will be passed to
        ``hook.define(<hook_label>)``.  Must be a list of strings.

        I.e. ``['my_custom_hook', 'some_other_hook']``
        """

        hooks = []
        """
        List of hooks to register when the app is created.  Will be passed to
        ``hook.register(<hook_label>, <hook_func>)``.  Must be a list of
        tuples in the form of ``(<hook_label>, <hook_func>)``.

        I.e. ``[('post_argument_parsing', my_hook_func)]``.
        """

        define_handlers = []
        """
        List of interfaces classes to define handlers.  Must be a list of
        uninstantiated interface classes.

        I.e. ``['MyCustomInterface', 'SomeOtherInterface']``
        """

        handlers = []
        """
        List of handler classes to register.  Will be passed to
        ``handler.register(<handler_class>)``.  Must be a list of
        uninstantiated handler classes.

        I.e. ``[MyCustomHandler, SomeOtherHandler]``
        """

    def __init__(self, label=None, **kw):
        super(CementApp, self).__init__(**kw)

        # disable framework logging?
        if 'CEMENT_FRAMEWORK_LOGGING' not in os.environ.keys():
            if self._meta.framework_logging is True:
                os.environ['CEMENT_FRAMEWORK_LOGGING'] = '1'
            else:
                os.environ['CEMENT_FRAMEWORK_LOGGING'] = '0'

        # for convenience we translate this to _meta
        if label:
            self._meta.label = label
        self._validate_label()
        self._loaded_bootstrap = None
        self._parsed_args = None
        self._last_rendered = None
        self.exit_code = 0

        self.ext = None
        self.config = None
        self.log = None
        self.plugin = None
        self.args = None
        self.output = None
        self.controller = None
        self.cache = None
        self.mail = None

        # setup argv... this has to happen before lay_cement()
        if self._meta.argv is None:
            self._meta.argv = list(sys.argv[1:])

        # hack for command line --debug
        if '--debug' in self.argv:
            self._meta.debug = True

        # setup the cement framework
        self._lay_cement()

    @property
    def debug(self):
        """
        Returns boolean based on whether `--debug` was passed at command line
        or set via the application's configuration file.

        :returns: boolean
        """
        return self._meta.debug

    @property
    def argv(self):
        """The arguments list that will be used when self.run() is called."""
        return self._meta.argv

    def extend(self, member_name, member_object):
        """
        Extend the CementApp() object with additional functions/classes such
        as 'app.my_custom_function()', etc.  It provides an interface for
        extensions to provide functionality that travel along with the
        application object.

        :param member_name: The name to attach the object to.
        :type member_name: str
        :param member_object: The function or class object to attach to
            CementApp().
        :raises: cement.core.exc.FrameworkError

        """
        if hasattr(self, member_name):
            raise exc.FrameworkError("App member '%s' already exists!" %
                                     member_name)
        LOG.debug("extending appication with '.%s' (%s)" %
                  (member_name, member_object))
        setattr(self, member_name, member_object)

    def _validate_label(self):
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

    def setup(self):
        """
        This function wraps all '_setup' actons in one call.  It is called
        before self.run(), allowing the application to be _setup but not
        executed (possibly letting the developer perform other actions
        before full execution.).

        All handlers should be instantiated and callable after setup is
        complete.

        """
        LOG.debug("now setting up the '%s' application" % self._meta.label)

        if self._meta.bootstrap is not None:
            LOG.debug("importing bootstrap code from %s" %
                      self._meta.bootstrap)

            if self._meta.bootstrap not in sys.modules \
                    or self._loaded_bootstrap is None:
                __import__(self._meta.bootstrap, globals(), locals(), [], 0)
                if hasattr(sys.modules[self._meta.bootstrap], 'load'):
                    sys.modules[self._meta.bootstrap].load(self)

                self._loaded_bootstrap = sys.modules[self._meta.bootstrap]
            else:
                reload(self._loaded_bootstrap)

        for res in hook.run('pre_setup', self):
            pass

        self._setup_signals()
        self._setup_extension_handler()
        self._setup_config_handler()
        self._setup_mail_handler()
        self._setup_cache_handler()
        self._setup_log_handler()
        self._setup_plugin_handler()
        self._setup_arg_handler()
        self._setup_output_handler()
        self._setup_controllers()

        for res in hook.run('post_setup', self):
            pass

    def run(self):
        """
        This function wraps everything together (after self._setup() is
        called) to run the application.

        """
        for res in hook.run('pre_run', self):
            pass

        # If controller exists, then pass controll to it
        if self.controller:
            self.controller._dispatch()
        else:
            self._parse_args()

        for res in hook.run('post_run', self):
            pass

    def __enter__(self):
        self.setup()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        # only close the app if there are no unhandled exceptions
        if exc_type is None:
            self.close()

    def close(self, code=None):
        """
        Close the application.  This runs the pre_close and post_close hooks
        allowing plugins/extensions/etc to 'cleanup' at the end of program
        execution.

        :param code: An exit code to exit with (`int`), if `None` is passed
         then exit with whatever `self.exit_code` is currently set to.

        """
        for res in hook.run('pre_close', self):
            pass

        LOG.debug("closing the application")

        for res in hook.run('post_close', self):
            pass

        if code is not None:
            assert type(code) == int, \
                "Invalid exit status code (must be integer)"
            self.exit_code = code

        if self._meta.exit_on_close is True:
            sys.exit(self.exit_code)

    def render(self, data, template=None, out=sys.stdout):
        """
        This is a simple wrapper around self.output.render() which simply
        returns an empty string if no self.output handler is defined.

        :param data: The data dictionary to render.
        :param template: The template to render to.  Default: None (some
            output handlers do not use templates).
        :param out: A file like object (sys.stdout, or actual file).  Set to
         ``None`` is no output is desired (just render and return).
         Default: sys.stdout

        """
        for res in hook.run('pre_render', self, data):
            if not type(res) is dict:
                LOG.debug("pre_render hook did not return a dict().")
            else:
                data = res

        if self.output is None:
            LOG.debug('render() called, but no output handler defined.')
            out_text = ''
        else:
            out_text = self.output.render(data, template)

        for res in hook.run('post_render', self, out_text):
            if not type(res) is str:
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

    def get_last_rendered(self):
        """
        DEPRECATION WARNING: This function is deprecated as of Cement 2.1.3
        in favor of the `self.last_rendered` property, and will be removed in
        future versions of Cement.

        Return the (data, output_text) tuple of the last time self.render()
        was called.

        :returns: tuple (data, output_text)

        """
        if not is_true(self._meta.ignore_deprecation_warnings):
            self.log.warn("Cement Deprecation Warning: " +
                          "CementApp.get_last_rendered() has been " +
                          "deprecated, and will be removed in future " +
                          "versions of Cement.  You should use the " +
                          "CementApp.last_rendered property instead.")
        return self._last_rendered

    @property
    def last_rendered(self):
        """
        Return the (data, output_text) tuple of the last time self.render() was
        called.

        :returns: tuple (data, output_text)

        """
        return self._last_rendered

    @property
    def pargs(self):
        """
        Returns the `parsed_args` object as returned by self.args.parse().
        """
        return self._parsed_args

    def add_arg(self, *args, **kw):
        """A shortcut for self.args.add_argument."""
        self.args.add_argument(*args, **kw)

    def _suppress_output(self):
        if self._meta.debug is True:
            LOG.debug('not suppressing console output because of debug mode')
            return

        LOG.debug('suppressing all console output')
        backend.__saved_stdout__ = sys.stdout
        backend.__saved_stderr__ = sys.stderr
        sys.stdout = NullOut()
        sys.stderr = NullOut()

    def _unsuppress_output(self):
        LOG.debug('unsuppressing all console output')
        sys.stdout = backend.__saved_stdout__
        sys.stderr = backend.__saved_stderr__

    def _lay_cement(self):
        """Initialize the framework."""
        LOG.debug("laying cement for the '%s' application" %
                  self._meta.label)

        if '--debug' in self._meta.argv:
            self._meta.debug = True
        elif '--quiet' in self._meta.argv:
            self._suppress_output()

        # start clean
        backend.__hooks__ = {}
        backend.__handlers__ = {}

        # define framework hooks
        hook.define('pre_setup')
        hook.define('post_setup')
        hook.define('pre_run')
        hook.define('post_run')
        hook.define('pre_argument_parsing')
        hook.define('post_argument_parsing')
        hook.define('pre_close')
        hook.define('post_close')
        hook.define('signal')
        hook.define('pre_render')
        hook.define('post_render')

        # define application hooks from meta
        for label in self._meta.define_hooks:
            hook.define(label)

        # register some built-in framework hooks
        hook.register('post_setup', add_handler_override_options, weight=-99)
        hook.register('post_argument_parsing', handler_override, weight=-99)

        # register application hooks from meta
        for label, func in self._meta.hooks:
            hook.register(label, func)

        # define and register handlers
        handler.define(extension.IExtension)
        handler.define(log.ILog)
        handler.define(config.IConfig)
        handler.define(mail.IMail)
        handler.define(plugin.IPlugin)
        handler.define(output.IOutput)
        handler.define(arg.IArgument)
        handler.define(controller.IController)
        handler.define(cache.ICache)

        # define application handlers
        for interface_class in self._meta.define_handlers:
            handler.define(interface_class)

        # extension handler is the only thing that can't be loaded... as,
        # well, an extension.  ;)
        handler.register(extension.CementExtensionHandler)

        # register application handlers
        for handler_class in self._meta.handlers:
            handler.register(handler_class)

    def _parse_args(self):
        for res in hook.run('pre_argument_parsing', self):
            pass

        self._parsed_args = self.args.parse(self.argv)

        if self._meta.arguments_override_config is True:
            for member in dir(self._parsed_args):
                if member and member.startswith('_'):
                    continue

                # don't override config values for options that weren't passed
                # or in otherwords are None
                elif getattr(self._parsed_args, member) is None:
                    continue

                for section in self.config.get_sections():
                    if member in self.config.keys(section):
                        self.config.set(section, member,
                                        getattr(self._parsed_args, member))

        for member in self._meta.override_arguments:
            for section in self.config.get_sections():
                if member in self.config.keys(section):
                    self.config.set(section, member,
                                    getattr(self._parsed_args, member))

        for res in hook.run('post_argument_parsing', self):
            pass

    def _setup_signals(self):
        if self._meta.catch_signals is None:
            LOG.debug("catch_signals=None... not handling any signals")
            return

        for signum in self._meta.catch_signals:
            LOG.debug("adding signal handler for signal %s" % signum)
            signal.signal(signum, self._meta.signal_handler)

    def _resolve_handler(self, handler_type, handler_def, raise_error=True):
        han = handler.resolve(handler_type, handler_def, raise_error)
        if han is not None:
            han._setup(self)
            return han

    def _setup_extension_handler(self):
        LOG.debug("setting up %s.extension handler" % self._meta.label)
        self.ext = self._resolve_handler('extension',
                                         self._meta.extension_handler)
        self.ext.load_extensions(self._meta.core_extensions)
        self.ext.load_extensions(self._meta.extensions)

    def _setup_config_handler(self):
        LOG.debug("setting up %s.config handler" % self._meta.label)
        self.config = self._resolve_handler('config',
                                            self._meta.config_handler)
        if self._meta.config_section is None:
            self._meta.config_section = self._meta.label
        self.config.add_section(self._meta.config_section)

        if self._meta.config_defaults is not None:
            self.config.merge(self._meta.config_defaults)

        if self._meta.config_files is None:
            label = self._meta.label

            self._meta.config_files = [
                os.path.join('/', 'etc', label, '%s.conf' % label),
                os.path.join(fs.HOME_DIR, '.%s.conf' % label),
                os.path.join(fs.HOME_DIR, '.%s' % label, 'config'),
            ]

        for _file in self._meta.config_files:
            self.config.parse_file(_file)

        self.validate_config()

        # hack for --debug
        if '--debug' in self.argv:
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
        if 'extensions' in self.config.keys(self._meta.label):
            exts = self.config.get(self._meta.label, 'extensions')

            # convert a comma-separated string to a list
            if type(exts) is str:
                ext_list = exts.split(',')

                # clean up extra space if they had it inbetween commas
                ext_list = [x.strip() for x in ext_list]

                # set the new extensions value in the config
                self.config.set(self._meta.label, 'extensions', ext_list)

            # otherwise, if it's a list (ConfigObj?)
            elif type(exts) is list:
                ext_list = exts

            for ext in ext_list:
                # load the extension
                self.ext.load_extension(ext)

                # add to meta data
                self._meta.extensions.append(ext)

    def _setup_mail_handler(self):
        LOG.debug("setting up %s.mail handler" % self._meta.label)
        self.mail = self._resolve_handler('mail',
                                          self._meta.mail_handler)

    def _setup_log_handler(self):
        LOG.debug("setting up %s.log handler" % self._meta.label)
        self.log = self._resolve_handler('log', self._meta.log_handler)

    def _setup_plugin_handler(self):
        LOG.debug("setting up %s.plugin handler" % self._meta.label)
        label = self._meta.label

        # plugin config dirs
        if self._meta.plugin_config_dirs is None:
            self._meta.plugin_config_dirs = [
                '/etc/%s/plugins.d/' % self._meta.label,
                os.path.join(fs.HOME_DIR, '.%s' % label, 'plugins.d'),
            ]
        config_dir = self._meta.plugin_config_dir
        if config_dir is not None:
            if config_dir not in self._meta.plugin_config_dirs:
                # append so that this config has precedence
                self._meta.plugin_config_dirs.append(config_dir)

        # plugin dirs
        if self._meta.plugin_dirs is None:
            self._meta.plugin_dirs = [
                os.path.join(fs.HOME_DIR, '.%s' % label, 'plugins'),
                '/usr/lib/%s/plugins' % self._meta.label,
            ]
        plugin_dir = self._meta.plugin_dir
        if plugin_dir is not None:
            if plugin_dir not in self._meta.plugin_dirs:
                # insert so that this dir has precedence
                self._meta.plugin_dirs.insert(0, plugin_dir)

        # plugin bootstrap
        if self._meta.plugin_bootstrap is None:
            self._meta.plugin_bootstrap = '%s.plugins' % self._meta.label

        self.plugin = self._resolve_handler('plugin',
                                            self._meta.plugin_handler)
        self.plugin.load_plugins(self._meta.plugins)
        self.plugin.load_plugins(self.plugin.get_enabled_plugins())

    def _setup_output_handler(self):
        if self._meta.output_handler is None:
            LOG.debug("no output handler defined, skipping.")
            return

        label = self._meta.label
        LOG.debug("setting up %s.output handler" % self._meta.label)
        self.output = self._resolve_handler('output',
                                            self._meta.output_handler,
                                            raise_error=False)
        # template module
        if self._meta.template_module is None:
            self._meta.template_module = '%s.templates' % label

        # template dirs
        if self._meta.template_dirs is None:
            self._meta.template_dirs = [
                os.path.join(fs.HOME_DIR, '.%s' % label, 'templates'),
                '/usr/lib/%s/templates' % label,
            ]
        template_dir = self._meta.template_dir
        if template_dir is not None:
            if template_dir not in self._meta.template_dirs:
                # insert so that this dir has precedence
                self._meta.template_dirs.insert(0, template_dir)

    def _setup_cache_handler(self):
        if self._meta.cache_handler is None:
            LOG.debug("no cache handler defined, skipping.")
            return

        LOG.debug("setting up %s.cache handler" % self._meta.label)
        self.cache = self._resolve_handler('cache',
                                           self._meta.cache_handler,
                                           raise_error=False)

    def _setup_arg_handler(self):
        LOG.debug("setting up %s.arg handler" % self._meta.label)
        self.args = self._resolve_handler('argument',
                                          self._meta.argument_handler)
        self.args.add_argument('--debug', dest='debug',
                               action='store_true',
                               help='toggle debug output')
        self.args.add_argument('--quiet', dest='suppress_output',
                               action='store_true',
                               help='suppress all output')

        # merge handler override meta data
        if self._meta.handler_override_options is not None:
            # fucking long names... fuck.  anyway, merge the core handler
            # override options with developer defined options
            core = self._meta.core_handler_override_options.copy()
            dev = self._meta.handler_override_options.copy()
            core.update(dev)

            self._meta.handler_override_options = core

    def _setup_controllers(self):
        LOG.debug("setting up application controllers")

        if self._meta.base_controller is not None:
            cntr = self._resolve_handler('controller',
                                         self._meta.base_controller)
            self.controller = cntr
            self._meta.base_controller = self.controller
        elif self._meta.base_controller is None:
            if handler.registered('controller', 'base'):
                self.controller = self._resolve_handler('controller', 'base')
                self._meta.base_controller = self.controller

        # This is necessary for some backend usage
        if self._meta.base_controller is not None:
            if self._meta.base_controller._meta.label != 'base':
                raise exc.FrameworkError("Base controllers must have " +
                                         "a label of 'base'.")

    def validate_config(self):
        """
        Validate application config settings.

        Usage:

        .. code-block:: python

            import os
            from cement.core import foundation

            class MyApp(foundation.CementApp):
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
