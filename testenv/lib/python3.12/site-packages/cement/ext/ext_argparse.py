"""
Cement argparse extension module.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from argparse import ArgumentParser, RawDescriptionHelpFormatter, SUPPRESS
from typing import Any, Callable, List, Dict, Tuple, Optional, TYPE_CHECKING
from ..core.arg import ArgumentHandler
from ..core.controller import ControllerHandler
from ..core.exc import FrameworkError
from ..utils.misc import minimal_logger

if TYPE_CHECKING:
    from ..core.foundation import App, ArgparseArgumentType  # pragma: nocover

LOG = minimal_logger(__name__)


def _clean_label(label: str) -> str:
    return re.sub('_', '-', label)


def _clean_func(func: str) -> Optional[str]:
    if func is None:
        return None
    else:
        return re.sub('-', '_', func)


class ArgparseArgumentHandler(ArgumentParser, ArgumentHandler):

    """
    This class implements the Argument Handler interface, and sub-classes
    from :py:class:`argparse.ArgumentParser`.
    Please reference the argparse documentation for full usage of the
    class.

    Arguments and keyword arguments are passed directly to ArgumentParser
    on initialization.
    """

    class Meta(ArgumentHandler.Meta):

        """Handler meta-data."""

        interface = 'argument'
        """The interface that this class implements."""

        label = 'argparse'
        """The string identifier of the handler."""

        ignore_unknown_arguments = False
        """
        Whether or not to ignore any arguments passed that are not defined.
        Default behavoir by Argparse is to raise an "unknown argument"
        exception by Argparse.

        This affectively triggers the difference between using ``parse_args``
        and ``parse_known_args``.  Unknown arguments will be accessible as
        ``unknown_args``.
        """

    _meta: Meta  # type: ignore

    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)
        self.config = None
        self.unknown_args = None
        self.parsed_args = None

    def parse(self, *args: List[str]) -> object:
        """
        Parse a list of arguments, and return them as an object.  Meaning an
        argument name of 'foo' will be stored as parsed_args.foo.

        Args:
            args (list): A list of arguments (generally sys.argv) to be
                parsed.

        Returns:
            object: Instance object whose members are the arguments parsed.

        """

        if self._meta.ignore_unknown_arguments is True:
            known_args, unknown_args = self.parse_known_args(*args)
            self.parsed_args = known_args  # type: ignore
            self.unknown_args = unknown_args  # type: ignore
        else:
            self.parsed_args = self.parse_args(*args)  # type: ignore
        return self.parsed_args

    def add_argument(self, *args: Any, **kw: Any) -> None:  # type: ignore
        """
        Add an argument to the parser.  Arguments and keyword arguments are
        passed directly to ``ArgumentParser.add_argument()``.
        See the :py:class:`argparse.ArgumentParser` documentation for help.
        """
        super().add_argument(*args, **kw)


@dataclass
class CommandMeta:
    label: str
    func_name: str
    exposed: bool
    hide: bool
    arguments: List[ArgparseArgumentType]
    parser_options: Dict[str, Any]
    controller: ArgparseController


class expose(object):

    """
    Used to expose functions to be listed as sub-commands under the
    controller namespace.  It also decorates the function with meta-data for
    the argument parser.

    Keyword Args:
        hide (bool): Whether the command should be visible.
        arguments (list): List of tuples that define arguments to add to this
            commands sub-parser.
        parser_options (dict): Additional options to pass to Argparse.
        label (str): String identifier for the command.

    Example:

        .. code-block:: python

            class Base(ArgparseController):
                class Meta:
                    label = 'base'

                # Note: Default functions only work in Python > 3.4
                @expose(hide=True)
                def default(self):
                    print("In Base.default()")

                @expose(
                    help='this is the help message for my_command',
                    aliases=['my_cmd'], # only available in Python 3+
                    arguments=[
                        (['-f', '--foo'],
                         dict(help='foo option', action='store', dest='foo')),
                    ]
                )
                def my_command(self):
                    print("In Base.my_command()")

    """
    # pylint: disable=W0622

    def __init__(self,
                 hide: bool = False,
                 arguments: List[ArgparseArgumentType] = [],
                 label: Optional[str] = None,
                 **parser_options: Any) -> None:
        self.hide = hide
        self.arguments = arguments
        self.label = label
        self.parser_options = parser_options

    def __call__(self, func: Callable) -> Callable:
        if self.label is None:
            self.label = func.__name__

        meta = CommandMeta(
            label=_clean_label(self.label),
            func_name=func.__name__,
            exposed=True,
            hide=self.hide,
            arguments=self.arguments,
            parser_options=self.parser_options,
            controller=None  # type: ignore
        )

        func.__cement_meta__ = meta
        return func


# shortcut for cleaner controllers
ex = expose


class ArgparseController(ControllerHandler):

    """
    This is an implementation of the Controller handler interface, and is a
    base class that application controllers should subclass from.  Registering
    it directly as a handler is useless.

    NOTE: This handler **requires** that the applications ``arg_handler`` be
    ``argparse``.  If using an alternative argument handler you will need to
    write your own controller base class or modify this one.

    Example:

        .. code-block:: python

            from cement.ext.ext_argparse import ArgparseController

            class Base(ArgparseController):
                class Meta:
                    label = 'base'
                    description = 'description at the top of --help'
                    epilog = "the text at the bottom of --help."
                    arguments = [
                        (
                            ['-f', '--foo'],
                            { 'help' : 'my foo option',
                              'dest' : 'foo' }
                        ),
                    ]

            class Second(ArgparseController):
                class Meta:
                    label = 'second'
                    stacked_on = 'base'
                    stacked_type = 'embedded'
                    arguments = [
                        (
                            ['--foo2'],
                            { 'help' : 'my foo2 option',
                              'dest' : 'foo2' }
                        ),
                    ]

    """

    class Meta(ControllerHandler.Meta):

        """
        Controller meta-data (can be passed as keyword arguments to the parent
        class).

        """

        # The interface this class implements.
        interface = 'controller'

        #: The string identifier for the controller.
        label: str = None  # type: ignore

        #: A list of aliases for the controller/sub-parser.  **Only available
        #: in Python > 3**.
        aliases: List[str] = []

        #: A config [section] to merge config_defaults into.  Cement will
        #: default to controller.<label> if None is set.
        config_section: str = None  # type: ignore

        #: Configuration defaults (type: dict) that are merged into the
        #: applications config object for the config_section mentioned above.
        config_defaults: Dict[str, Any] = {}

        #: Arguments to pass to the argument_handler.  The format is a list
        #: of tuples whos items are a ( list, dict ).  Meaning:
        #:
        #: ``[ ( ['-f', '--foo'], dict(help='foo option', dest='foo') ), ]``
        #:
        #: This is equivelant to manually adding each argument to the argument
        #: parser as in the following example:
        #:
        #: ``add_argument('-f', '--foo', help='foo option', dest='foo')``
        arguments: List[ArgparseArgumentType] = []

        #: A label of another controller to 'stack' commands/arguments on top
        #: of.
        stacked_on = 'base'

        #: Whether to embed commands and arguments within the parent
        #: controller's namespace, or to nest this controller under the parent
        #: controller (making it a sub-command).  Must be one of
        #: ``['embedded', 'nested']``.
        stacked_type = 'embedded'

        #: Description for the sub-parser group in help output.
        description = None

        #: The title for the sub-parser group in help output.
        title = 'sub-commands'

        #: Text for the controller/sub-parser group in help output (for
        #: nested stacked controllers only).
        help: str = None  # type: ignore

        #: Whether or not to hide the controller entirely.
        hide = False

        #: The text that is displayed at the bottom when ``--help`` is passed.
        epilog: Optional[str] = None

        #: The text that is displayed at the top when ``--help`` is passed.
        #: Defaults to Argparse standard usage.
        usage: Optional[str] = None

        #: The argument formatter class to use to display ``--help`` output.
        argument_formatter = RawDescriptionHelpFormatter

        #: Additional keyword arguments passed when
        #: ``ArgumentParser.add_subparsers()`` is called to create this
        #: controller namespace.  WARNING: This could break things, use at
        #: your own risk.  Useful if you need additional features from
        #: Argparse that is not built into the controller Meta-data.
        subparser_options: Dict = {}

        #: Additional keyword arguments passed when
        #: ``ArgumentParser.add_parser()`` is called to create this
        #: controller sub-parser.  WARNING: This could break things, use at
        #: your own risk.  Useful if you need additional features from
        #: Argparse that is not built into the controller Meta-data.
        parser_options: Dict = {}

        #: Function to call if no sub-command is passed.  By default this is
        #: ``_default``, which is equivelant to passing ``-h/--help``. It
        #: should be noted that this is the only place where having a command
        #: function start with ``_`` is OK simply because we treat it as a
        #: special case (different that other exposed commands).
        #:
        #: If set to ``None``, Cement will simply pass and exit 0.
        #:
        #: Note: Currently, default function/sub-command only works on
        #: Python > 3.4.  Previous versions of Python/Argparse will throw the
        #: exception ``error: too few arguments``.
        default_func: str = '_default'

    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)
        self.app: App = None  # type: ignore
        self._parser: ArgumentParser = None  # type: ignore

        if self._meta.label == 'base':
            self._sub_parser_parents: Dict[str, Any] = dict()
            self._sub_parsers: Dict[str, Any] = dict()
            self._controllers: List[ArgparseController] = []
            self._controllers_map: Dict[str, ArgparseController] = {}

        if self._meta.help is None:
            self._meta.help = f'{_clean_label(self._meta.label)} controller'

    def _default(self) -> None:
        self._parser.print_help()

    def _validate(self) -> None:
        try:
            assert self._meta.stacked_type in ['embedded', 'nested'], \
                f"Invalid stacked type {self._meta.stacked_type}.  " \
                + "Expecting one of: [embedded, nested]"
        except AssertionError as e:
            raise FrameworkError(e.args[0])

    def _setup_controllers(self) -> None:
        # need a list to maintain order
        resolved_controllers: List[ArgparseController] = []

        # need a dict to do key/label based lookup
        resolved_controllers_map: Dict[str, ArgparseController] = {}

        # list to maintain which controllers we haven't resolved yet
        unresolved_controllers: List[ArgparseController] = []

        for ctrl in self.app.handler.list('controller'):
            # don't include self/base
            if ctrl == self.__class__:
                continue

            handler: ArgparseController
            handler = self.app.handler.resolve('controller', ctrl, setup=True)  # type: ignore
            unresolved_controllers.append(handler)

        # treat self/base separately
        resolved_controllers.append(self)
        resolved_controllers_map['base'] = self

        # all this crazy shit is to resolve controllers in the order that they
        # are nested/embedded, otherwise argparse does weird things

        LOG.debug('resolving controller nesting/embedding order')

        current_parent = self._meta.label
        while unresolved_controllers:
            LOG.debug(f'unresolved controllers > {unresolved_controllers}')
            LOG.debug(f'current parent > {current_parent}')

            # handle all controllers nested on parent
            current_children: List[ArgparseController] = []
            resolved_child_controllers: List[ArgparseController] = []

            for contr in list(unresolved_controllers):
                # if stacked_on is the current parent, we want to process
                # its children in this run first
                if contr._meta.stacked_on == current_parent:
                    current_children.append(contr)
                    if contr._meta.stacked_type == 'embedded':
                        resolved_child_controllers.append(contr)
                    else:
                        resolved_child_controllers.insert(0, contr)
                    unresolved_controllers.remove(contr)
                    LOG.debug('resolved controller %s %s on %s' %
                              (contr, contr._meta.stacked_type,
                               current_parent))

                # if not, fall back on whether the stacked_on parent is
                # already resolved
                elif contr._meta.stacked_on in resolved_controllers_map.keys():
                    resolved_controllers.append(contr)
                    resolved_controllers_map[contr._meta.label] = contr
                    unresolved_controllers.remove(contr)
                    LOG.debug('resolved controller %s %s on %s' %
                              (contr, contr._meta.stacked_type,
                               contr._meta.stacked_on))

            resolved_controllers.extend(resolved_child_controllers)
            for contr in resolved_child_controllers:
                resolved_controllers_map[contr._meta.label] = contr

            # then, for all those controllers... handler all controllers
            # nested on them
            resolved_child_controllers = []
            for child_contr in current_children:
                for contr in list(unresolved_controllers):
                    if contr._meta.stacked_on == child_contr._meta.label:
                        if contr._meta.stacked_type == 'embedded':
                            resolved_child_controllers.append(contr)
                        else:
                            resolved_child_controllers.insert(0, contr)

                        unresolved_controllers.remove(contr)
                        LOG.debug('resolved controller %s %s on %s' %
                                  (contr, contr._meta.stacked_type,
                                   child_contr._meta.label))

            resolved_controllers.extend(resolved_child_controllers)
            for contr in resolved_child_controllers:
                resolved_controllers_map[contr._meta.label] = contr

            # re-iterate with the next in line as the parent (handles multiple
            # level nesting)
            if unresolved_controllers:
                current_parent = unresolved_controllers[0]._meta.label

        self._controllers = resolved_controllers
        self._controllers_map = resolved_controllers_map

    def _process_parsed_arguments(self) -> None:
        pass

    def _get_subparser_options(self, contr: ArgparseController) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = contr._meta.subparser_options.copy()

        if 'title' not in kwargs.keys():
            kwargs['title'] = contr._meta.title

        kwargs['dest'] = 'command'

        return kwargs

    def _get_parser_options(self, contr: ArgparseController) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = contr._meta.parser_options.copy()

        if 'aliases' not in kwargs.keys():
            kwargs['aliases'] = contr._meta.aliases

        if 'description' not in kwargs.keys():
            kwargs['description'] = contr._meta.description
        if 'usage' not in kwargs.keys():
            kwargs['usage'] = contr._meta.usage
        if 'epilog' not in kwargs.keys():
            kwargs['epilog'] = contr._meta.epilog
        if 'help' not in kwargs.keys():
            kwargs['help'] = contr._meta.help

        if contr._meta.hide is True:
            if 'help' in kwargs.keys():
                del kwargs['help']
        else:
            kwargs['help'] = contr._meta.help

        return kwargs

    def _get_command_parser_options(self, command: CommandMeta) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = command.parser_options.copy()

        contr = command.controller

        hide_it = False
        if command.hide is True:
            hide_it = True

        # only hide commands from embedded controllers if the controller is
        # hidden
        elif contr._meta.stacked_type == 'embedded' \
                and contr._meta.hide is True:
            hide_it = True

        if hide_it is True:
            if 'help' in kwargs:
                del kwargs['help']

        return kwargs

    def _setup_parsers(self) -> None:
        # this should only be run by the base controller
        from cement.utils.misc import rando

        _rando = rando()[:12]
        self._dispatch_option = f'--dispatch-{_rando}'
        self._controller_option = f'--controller-namespace-{_rando}'

        # parents are sub-parser namespaces (that we can add subparsers to)
        # where-as parsers are the actual root parser and sub-parsers to
        # add arguments to
        parents = self._sub_parser_parents
        parsers = self._sub_parsers
        parsers['base'] = self.app.args
        # parsers['base'] = ArgumentParser()
        # sub1 = parsers['base'].add_subparsers(title='sub-commands')
        # sub1.add_parser('johnny')
        # parsers['base'].parse_args()

        kwargs = self._get_subparser_options(self)

        # only create a subparser if there are commands or nested
        # controllers
        cmds = self._collect_commands()
        contrs = [x for x in self._controllers
                  if x._meta.label != self._meta.label and
                  x._meta.stacked_on == self._meta.label]

        if len(cmds) > 0 or len(contrs) > 0:
            sub = self.app.args.add_subparsers(**kwargs)
            parents['base'] = sub

        base_parser_options = self._get_parser_options(self)
        for key, val in base_parser_options.items():
            setattr(self.app.args, key, val)

        # handle base controller separately
        parsers['base'].add_argument(self._controller_option,
                                     action='store',
                                     default='base',
                                     nargs='?',
                                     help=SUPPRESS,
                                     dest='__controller_namespace__',
                                     )
        self._parser = parsers['base']
        self._parser.formatter_class = self._meta.argument_formatter

        # and if only base controller registered... go ahead and return
        if len(self.app.handler.list('controller')) <= 1:
            return    # pragma: nocover

        # note that the order of self._controllers was already organized by
        # stacking/embedding order in self._setup_controllers ... order is
        # important here otherwise argparse does wierd things
        for contr in self._controllers:
            label = contr._meta.label
            stacked_on = contr._meta.stacked_on
            stacked_type = contr._meta.stacked_type

            if stacked_type == 'nested':
                # if the controller is nested, we need to create a new parser
                # parent using the one that it is stacked on, as well as as a
                # new parser
                kwargs = self._get_parser_options(contr)
                parsers[label] = parents[stacked_on].add_parser(
                    _clean_label(label),
                    **kwargs
                )

                contr._parser = parsers[label]

                # we need to add subparsers to this parser so we can
                # attach commands and other nested controllers to it
                kwargs = self._get_subparser_options(contr)

                # only create a subparser if there are commands or nested
                # controllers
                cmds = contr._collect_commands()
                contrs = [x for x in self._controllers
                          if x._meta.label != label and
                          x._meta.stacked_on == label]

                if len(cmds) > 0 or len(contrs) > 0:
                    parents[label] = parsers[label].add_subparsers(**kwargs)

                # add an invisible controller option so we can figure out what
                # to call later in self._dispatch
                parsers[label].add_argument(self._controller_option,
                                            action='store',
                                            default=contr._meta.label,
                                            help=SUPPRESS,
                                            dest='__controller_namespace__',
                                            )
                parsers[label].formatter_class = contr._meta.argument_formatter

            elif stacked_type == 'embedded':
                # if it's embedded, then just set it to use the same as the
                # controller it's stacked on
                parents[label] = parents[stacked_on]
                parsers[label] = parsers[stacked_on]
                contr._parser = parsers[stacked_on]

    def _get_parser_by_controller(self, controller: ArgparseController) -> ArgumentParser:
        if controller._meta.stacked_type == 'embedded':
            parser = self._get_parser(controller._meta.stacked_on)
        else:
            parser = self._get_parser(controller._meta.label)

        return parser

    def _get_parser_parent_by_controller(self, controller: ArgparseController) -> ArgumentParser:
        if controller._meta.stacked_type == 'embedded':
            parent = self._get_parser_parent(controller._meta.stacked_on)
        else:
            parent = self._get_parser_parent(controller._meta.label)

        return parent

    def _get_parser_parent(self, label: str) -> ArgumentParser:
        return self._sub_parser_parents[label]  # type: ignore

    def _get_parser(self, label: str) -> ArgumentParser:
        return self._sub_parsers[label]  # type: ignore

    def _process_arguments(self, controller: ArgparseController) -> None:
        label = controller._meta.label

        LOG.debug(f"processing arguments for '{label}' " +
                  "controller namespace")

        parser = self._get_parser_by_controller(controller)
        arguments = controller._collect_arguments()
        for arg, kw in arguments:
            LOG.debug(f'adding argument (args={arg}, kwargs={kw})')
            parser.add_argument(*arg, **kw)

    def _process_commands(self, controller: ArgparseController) -> None:
        label = controller._meta.label
        LOG.debug(f"processing commands for '{label}' " +
                  "controller namespace")

        commands = controller._collect_commands()
        for command in commands:
            kwargs = self._get_command_parser_options(command)

            func_name = command.func_name
            LOG.debug(f"adding command '{command.label}' " +
                      f"(controller={controller._meta.label}, func={func_name})")

            cmd_parent = self._get_parser_parent_by_controller(controller)
            command_parser = cmd_parent.add_parser(command.label, **kwargs)

            # add an invisible dispatch option so we can figure out what to
            # call later in self._dispatch
            default_contr_func = "%s.%s" % (command.controller._meta.label,
                                            command.func_name)
            command_parser.add_argument(self._dispatch_option,
                                        action='store',
                                        default=default_contr_func,
                                        help=SUPPRESS,
                                        dest='__dispatch__',
                                        )

            # add additional arguments to the sub-command namespace
            LOG.debug(f"processing arguments for '{command.label}' " +
                      "command namespace")
            for arg, kw in command.arguments:
                LOG.debug(f'adding argument (args={arg}, kwargs={kw})')
                command_parser.add_argument(*arg, **kw)

    def _collect(self) -> Tuple[List[ArgparseArgumentType], List[CommandMeta]]:
        arguments = self._collect_arguments()
        commands = self._collect_commands()
        return (arguments, commands)

    def _collect_arguments(self) -> List[ArgparseArgumentType]:
        LOG.debug(f"collecting arguments from {self} " +
                  "(stacked_on='%s', stacked_type='%s')" %
                  (self._meta.stacked_on, self._meta.stacked_type))
        return self._meta.arguments  # type: ignore

    def _collect_commands(self) -> List[CommandMeta]:
        LOG.debug(f"collecting commands from {self} " +
                  "(stacked_on='%s', stacked_type='%s')" %
                  (self._meta.stacked_on, self._meta.stacked_type))

        commands = []
        for member in dir(self.__class__):
            if member.startswith('_'):
                continue
            elif hasattr(getattr(self, member), '__cement_meta__'):
                func: CommandMeta = getattr(self.__class__, member).__cement_meta__
                func.controller = self
                commands.append(func)

        return commands

    def _get_exposed_commands(self) -> List[str]:
        """
        Get a list of exposed commands for this controller

        Returns:

            exposed_commands (list): List of exposed commands (labels)
        """
        # get exposed commands
        exposed = []
        for member_key in dir(self):
            member = getattr(self, member_key)
            if hasattr(member, '__cement_meta__'):
                exposed.append(_clean_label(member_key))
        return exposed

    def _pre_argument_parsing(self) -> None:
        """
        Called on every controller just before arguments are parsed.
        Provides an alternative means of adding arguments to the controller,
        giving more control than using ``Meta.arguments``.

        Example:

            .. code-block:: python

                class Base(ArgparseController):
                    class Meta:
                        label = 'base'

                    def _pre_argument_parsing(self):
                        p = self._parser
                        p.add_argument('-f', '--foo',
                                       help='my foo option',
                                       dest='foo')

                    def _post_argument_parsing(self):
                        if self.app.pargs.foo:
                            print('Got Foo Option Before Controller Dispatch')

        """
        pass

    def _post_argument_parsing(self) -> None:
        """
        Called on every controller just after arguments are parsed (assuming
        that the parser hasn't thrown an exception).  Provides an alternative
        means of handling passed arguments.  Note that, this function is
        called on every controller, regardless of what namespace and
        sub-command is eventually going to be called.  Therefore, every
        controller can handle their arguments if the user passed them.

        For example:

        .. code-block:: console

            $ myapp --foo bar some-controller --foo2 bar2 some-command


        In the above, the ``base`` controller (or a nested controller) would
        handle ``--foo``, while ``some-controller`` would handle ``foo2``
        before ``some-command`` is executed.

        .. code-block:: python

            class Base(ArgparseController):
                class Meta:
                    label = 'base'

                    arguments = [
                        (['-f', '--foo'],
                         dict(help='my foo option', dest=foo)),
                    ]

                def _post_argument_parsing(self):
                    if self.app.pargs.foo:
                        print('Got Foo Option Before Controller Dispatch')

        Note that ``self._parser`` within a controller is that individual
        controllers ``sub-parser``, and is not the root parser ``app.args``
        (unless you are the ``base`` controller, in which case
        ``self._parser`` is synonymous with ``app.args``).

        """
        pass

    def _dispatch(self) -> Any:
        LOG.debug(f"controller dispatch passed off to {self}")
        self._setup_controllers()
        self._setup_parsers()

        for contr in self._controllers:
            self._process_arguments(contr)
            self._process_commands(contr)

        for contr in self._controllers:
            contr._pre_argument_parsing()

        self.app._parse_args()

        for contr in self._controllers:
            contr._post_argument_parsing()
            contr._process_parsed_arguments()

        if hasattr(self.app.pargs, '__dispatch__'):
            # if __dispatch__ is set that means that we have hit a sub-command
            # of a controller.
            contr_label = self.app.pargs.__dispatch__.split('.')[0]
            func_name = self.app.pargs.__dispatch__.split('.')[1]
        else:
            # if no __dispatch__ is set then that means we have hit a
            # controller with not sub-command (argparse doesn't support
            # default sub-command yet... so we rely on
            # __controller_namespace__ and its default func

            # We never get here on Python < 3 as Argparse would have already
            # complained about too few arguments
            contr_label = self.app.pargs\
                              .__controller_namespace__     # pragma: nocover
            contr = self._controllers_map[contr_label]      # pragma: nocover
            func_name = _clean_func(                        # pragma: nocover
                contr._meta.default_func                    # pragma: nocover
            )                                               # pragma: nocover

        if contr_label == 'base':
            contr = self
        else:
            contr = self._controllers_map[contr_label]

        if func_name is None:
            pass    # pragma: nocover
        elif hasattr(contr, func_name):
            func = getattr(contr, func_name)
            return func()
        else:
            # only time that we'd get here is if Controller.Meta.default_func
            # is pointing to something that doesn't exist
            #
            # We never get here on Python < 3 as Argparse would have already
            # complained about too few arguments
            raise FrameworkError(                           # pragma: nocover
                "Controller function does not exist %s.%s()" %
                (contr.__class__.__name__, func_name))      # pragma: nocover


def load(app: App) -> None:
    app.handler.register(ArgparseArgumentHandler)
