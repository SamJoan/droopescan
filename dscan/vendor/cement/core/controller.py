"""Cement core controller module."""

import re
import textwrap
import argparse
from ..core import exc, interface, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


def controller_validator(klass, obj):
    """
    Validates a handler implementation against the IController interface.

    """
    members = [
        '_setup',
        '_dispatch',
    ]
    meta = [
        'label',
        'aliases',
        'interface',
        'description',
        'config_section',
        'config_defaults',
        'arguments',
        'usage',
        'epilog',
        'stacked_on',
        'stacked_type',
        'hide',
    ]
    interface.validate(IController, obj, members, meta=meta)

    # also check _meta.arguments values
    errmsg = "Controller arguments must be a list of tuples.  I.e. " + \
             "[ (['-f', '--foo'], dict(action='store')), ]"

    if obj._meta.arguments is not None:
        if type(obj._meta.arguments) is not list:
            raise exc.InterfaceError(errmsg)
        for item in obj._meta.arguments:
            if type(item) is not tuple:
                raise exc.InterfaceError(errmsg)
            if type(item[0]) is not list:
                raise exc.InterfaceError(errmsg)
            if type(item[1]) is not dict:
                raise exc.InterfaceError(errmsg)


class IController(interface.Interface):

    """
    This class defines the Controller Handler Interface.  Classes that
    implement this handler must provide the methods and attributes defined
    below.

    Implementations do *not* subclass from interfaces.

    Usage:

    .. code-block:: python

        from cement.core import controller

        class MyBaseController(controller.CementBaseController):
            class Meta:
                interface = controller.IController
                ...
    """
    # pylint: disable=W0232, C0111, R0903
    class IMeta:

        """Interface meta-data."""

        label = 'controller'
        """The string identifier of the interface."""

        validator = controller_validator
        """The interface validator function."""

    # Must be provided by the implementation
    Meta = interface.Attribute('Handler meta-data')

    def _setup(app_obj):
        """
        The _setup function is after application initialization and after it
        is determined that this controller was requested via command line
        arguments.  Meaning, a controllers _setup() function is only called
        right before it's _dispatch() function is called to execute a command.
        Must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object.
        :returns: None

        """

    def _dispatch(self):
        """
        Reads the application object's data to dispatch a command from this
        controller.  For example, reading self.app.pargs to determine what
        command was passed, and then executing that command function.

        Note that Cement does *not* parse arguments when calling _dispatch()
        on a controller, as it expects the controller to handle parsing
        arguments (I.e. self.app.args.parse()).

        :returns: None

        """


class expose(object):

    """
    Used to expose controller functions to be listed as commands, and to
    decorate the function with Meta data for the argument parser.

    :param help: Help text to display for that command.
    :type help: str
    :param hide: Whether the command should be visible.
    :type hide: boolean
    :param aliases: Aliases to this command.
    :param aliases_only: Whether to only display the aliases (not the label).
     This is useful for situations where you have obscure function names
     which you do not want displayed.  Effecively, if there are aliases and
     `aliases_only` is True, then aliases[0] will appear as the actual
     command/function label.
    :type aliases: list

    Usage:

    .. code-block:: python

        from cement.core.controller import CementBaseController, expose

        class MyAppBaseController(CementBaseController):
            class Meta:
                label = 'base'

            @expose(hide=True, aliases=['run'])
            def default(self):
                print("In MyAppBaseController.default()")

            @expose()
            def my_command(self):
                print("In MyAppBaseController.my_command()")

    """
    # pylint: disable=W0622

    def __init__(self, help='', hide=False, aliases=[], aliases_only=False):
        self.hide = hide
        self.help = help
        self.aliases = aliases
        self.aliases_only = aliases_only

    def __call__(self, func):
        metadict = {}
        metadict['label'] = re.sub('_', '-', func.__name__)
        metadict['func_name'] = func.__name__
        metadict['exposed'] = True
        metadict['hide'] = self.hide
        metadict['help'] = self.help
        metadict['aliases'] = self.aliases
        metadict['aliases_only'] = self.aliases_only
        metadict['controller'] = None  # added by the controller
        func.__cement_meta__ = metadict
        return func


# pylint: disable=R0921
class CementBaseController(handler.CementBaseHandler):

    """
    This is an implementation of the
    `IControllerHandler <#cement.core.controller.IController>`_ interface, but
    as a base class that application controllers `should` subclass from.
    Registering it directly as a handler is useless.

    NOTE: This handler **requires** that the applications 'arg_handler' be
    argparse.  If using an alternative argument handler you will need to
    write your own controller base class.

    Usage:

    .. code-block:: python

        from cement.core import controller

        class MyAppBaseController(controller.CementBaseController):
            class Meta:
                label = 'base'
                description = 'MyApp is awesome'
                config_defaults = dict()
                arguments = []
                epilog = "This is the text at the bottom of --help."
                # ...

        class MyStackedController(controller.CementBaseController):
            class Meta:
                label = 'second_controller'
                aliases = ['sec', 'secondary']
                stacked_on = 'base'
                stacked_type = 'embedded'
                # ...

    """
    class Meta:

        """
        Controller meta-data (can be passed as keyword arguments to the parent
        class).

        """

        interface = IController
        """The interface this class implements."""

        label = None
        """The string identifier for the controller."""

        aliases = []
        """
        A list of aliases for the controller.  Will be treated like
        command/function aliases for non-stacked controllers.  For example:
        'myapp <controller_label> --help' is the same as
        'myapp <controller_alias> --help'.
        """

        aliases_only = False
        """
        When set to True, the controller label will not be displayed at
        command line, only the aliases will.  Effectively, aliases[0] will
        appear as the label.  This feature is useful for the situation Where
        you might want two controllers to have the same label when stacked
        on top of separate controllers.  For example, 'myapp users list' and
        'myapp servers list' where 'list' is a stacked controller, not a
        function.
        """

        description = None
        """The description shown at the top of '--help'.  Default: None"""

        config_section = None
        """
        A config [section] to merge config_defaults into.  Cement will default
        to controller.<label> if None is set.
        """

        config_defaults = {}
        """
        Configuration defaults (type: dict) that are merged into the
        applications config object for the config_section mentioned above.
        """

        arguments = []
        """
        Arguments to pass to the argument_handler.  The format is a list
        of tuples whos items are a ( list, dict ).  Meaning:

        ``[ ( ['-f', '--foo'], dict(dest='foo', help='foo option') ), ]``

        This is equivelant to manually adding each argument to the argument
        parser as in the following example:

        ``parser.add_argument(['-f', '--foo'], help='foo option', dest='foo')``

        """

        stacked_on = 'base'
        """
        A label of another controller to 'stack' commands/arguments on top of.
        """

        stacked_type = 'embedded'
        """
        Whether to `embed` commands and arguments within the parent controller
        or to simply `nest` the controller under the parent controller (making
        it a sub-sub-command).  Must be one of `['embedded', 'nested']` only
        if `stacked_on` is not `None`.
        """

        hide = False
        """Whether or not to hide the controller entirely."""

        epilog = None
        """
        The text that is displayed at the bottom when '--help' is passed.
        """

        usage = None
        """
        The text that is displayed at the top when '--help' is passed.
        Although the default is `None`, Cement will set this to a generic
        usage based on the `prog`, `controller` name, etc if nothing else is
        passed.
        """

        argument_formatter = argparse.RawDescriptionHelpFormatter
        """
        The argument formatter class to use to display --help output.
        """

        default_func = 'default'
        """
        Function to call if no sub-command is passed.  Note that this can
        **not** start with an ``_`` due to backward compatibility restraints
        in how Cement discovers and maps commands.
        """

    def __init__(self, *args, **kw):
        super(CementBaseController, self).__init__(*args, **kw)

        self.app = None
        self._commands = {}  # used to store collected commands
        self._visible_commands = []  # used to sort visible command labels
        self._arguments = []  # used to store collected arguments
        self._dispatch_map = {}  # used to map commands/aliases to controller
        self._dispatch_command = None  # set during _parse_args()

    def _setup(self, app_obj):
        """
        See `IController._setup() <#cement.core.cache.IController._setup>`_.
        """
        super(CementBaseController, self)._setup(app_obj)

        if getattr(self._meta, 'description', None) is None:
            self._meta.description = "%s Controller" % \
                self._meta.label.capitalize()

        self.app = app_obj

    def _collect(self):
        self.app.log.debug("collecting arguments/commands for %s" % self)
        arguments = []
        commands = []

        # process my arguments and commands first
        arguments = list(self._meta.arguments)

        for member in dir(self.__class__):
            if member.startswith('_'):
                continue
            try:
                func = getattr(self.__class__, member).__cement_meta__
            except AttributeError:
                continue
            else:
                func['controller'] = self
                commands.append(func)

        # process stacked controllers second for commands and args
        for contr in handler.list('controller'):
            # don't include self here
            if contr == self.__class__:
                continue

            contr = contr()
            contr._setup(self.app)
            if contr._meta.stacked_on == self._meta.label:
                if contr._meta.stacked_type == 'embedded':
                    contr_arguments, contr_commands = contr._collect()
                    for arg in contr_arguments:
                        arguments.append(arg)
                    for func in contr_commands:
                        commands.append(func)
                elif contr._meta.stacked_type == 'nested':
                    metadict = {}
                    metadict['label'] = re.sub('_', '-', contr._meta.label)
                    metadict['func_name'] = '_dispatch'
                    metadict['exposed'] = True
                    metadict['hide'] = contr._meta.hide
                    metadict['help'] = contr._meta.description
                    metadict['aliases'] = contr._meta.aliases
                    metadict['aliases_only'] = contr._meta.aliases_only
                    metadict['controller'] = contr
                    commands.append(metadict)
                else:
                    raise exc.FrameworkError(
                        "Controller '%s' " % contr._meta.label +
                        "has an unknown stacked type of '%s'." %
                        contr._meta.stacked_type
                    )
        return (arguments, commands)

    def _process_arguments(self):
        for _arg, _kw in self._arguments:
            try:
                self.app.args.add_argument(*_arg, **_kw)
            except argparse.ArgumentError as e:
                raise exc.FrameworkError(e.__str__())

    def _process_commands(self):
        self._dispatch_map = {}
        self._visible_commands = []

        for cmd in self._commands:
            # process command labels
            if cmd['label'] in self._dispatch_map.keys():
                raise exc.FrameworkError(
                    "Duplicate command named '%s' " % cmd['label'] +
                    "found in controller '%s'" % cmd['controller']
                )
            self._dispatch_map[cmd['label']] = cmd

            if not cmd['hide']:
                self._visible_commands.append(cmd['label'])

            # process command aliases
            for alias in cmd['aliases']:
                if alias in self._dispatch_map.keys():
                    raise exc.FrameworkError(
                        "The alias '%s' of the " % alias +
                        "'%s' controller collides " % cmd['controller'] +
                        "with a command or alias of the same name."
                    )
                self._dispatch_map[alias] = cmd
        self._visible_commands.sort()

    def _get_dispatch_command(self):
        default_func = self._meta.default_func
        default_func_key = re.sub('_', '-', self._meta.default_func)

        if (len(self.app.argv) <= 0) or (self.app.argv[0].startswith('-')):
            # if no command is passed, then use default
            if default_func_key in self._dispatch_map.keys():
                self._dispatch_command = self._dispatch_map[default_func_key]

        elif self.app.argv[0] in self._dispatch_map.keys():
            self._dispatch_command = self._dispatch_map[self.app.argv[0]]
            self.app.argv.pop(0)
        else:
            # check for default again (will get here if command line has
            # positional arguments that don't start with a -)
            if default_func_key in self._dispatch_map.keys():
                self._dispatch_command = self._dispatch_map[default_func_key]

    def _parse_args(self):
        self.app.args.description = self._help_text
        self.app.args.usage = self._usage_text
        self.app.args.formatter_class = self._meta.argument_formatter
        self.app._parse_args()

    def _dispatch(self):
        """
        Takes the remaining arguments from self.app.argv and parses for a
        command to dispatch, and if so... dispatches it.

        """
        if hasattr(self._meta, 'epilog'):
            if self._meta.epilog is not None:
                self.app.args.epilog = self._meta.epilog

        self._arguments, self._commands = self._collect()
        self._process_commands()
        self._get_dispatch_command()

        if self._dispatch_command:
            if self._dispatch_command['func_name'] == '_dispatch':
                func = getattr(self._dispatch_command['controller'],
                               '_dispatch')
                return func()
            else:
                self._process_arguments()
                self._parse_args()
                func = getattr(self._dispatch_command['controller'],
                               self._dispatch_command['func_name'])
                return func()
        else:
            self._process_arguments()
            self._parse_args()

    @property
    def _usage_text(self):
        """Returns the usage text displayed when '--help' is passed."""

        if self._meta.usage is not None:
            return self._meta.usage

        txt = "%s (sub-commands ...) [options ...] {arguments ...}" % \
              self.app.args.prog
        return txt

    @property
    def _help_text(self):
        """Returns the help text displayed when '--help' is passed."""

        cmd_txt = ''
        for label in self._visible_commands:
            cmd = self._dispatch_map[label]
            if len(cmd['aliases']) > 0 and cmd['aliases_only']:
                if len(cmd['aliases']) > 1:
                    first = cmd['aliases'].pop(0)
                    cmd_txt = cmd_txt + "  %s (aliases: %s)\n" % \
                        (first, ', '.join(cmd['aliases']))
                else:
                    cmd_txt = cmd_txt + "  %s\n" % cmd['aliases'][0]
            elif len(cmd['aliases']) > 0:
                cmd_txt = cmd_txt + "  %s (aliases: %s)\n" % \
                    (label, ', '.join(cmd['aliases']))
            else:
                cmd_txt = cmd_txt + "  %s\n" % label

            if cmd['help']:
                cmd_txt = cmd_txt + "    %s\n\n" % cmd['help']
            else:
                cmd_txt = cmd_txt + "\n"

        if len(cmd_txt) > 0:
            txt = '''%s

commands:

%s


        ''' % (self._meta.description, cmd_txt)
        else:
            txt = self._meta.description

        return textwrap.dedent(txt)
