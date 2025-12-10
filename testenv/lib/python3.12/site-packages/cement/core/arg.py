"""
Cement core argument module.

"""

from abc import abstractmethod
from typing import Any, List
from ..core.interface import Interface
from ..core.handler import Handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class ArgumentInterface(Interface):

    """
    This class defines the Argument Interface.  Handlers that implement this
    interface must provide the methods and attributes defined below. In
    general, most implementations should sub-class from the provided
    :class:`ArgumentHandler` base class as a starting point.
    """

    class Meta(Interface.Meta):

        """Interface meta-data options."""

        #: The string identifier of the interface.
        interface = 'argument'

    @abstractmethod
    def add_argument(self, *args: str, **kw: Any) -> None:
        """Add arguments to the parser.

        This should be ``-o/--option`` or positional. Note that the interface
        defines the following parameters so that at the very least, external
        extensions can guarantee that they can properly add command line
        arguments when necessary.  The implementation itself should, and will
        provide and support many more options than those listed here.  That
        said, the implementation must support the following:

        Args:
            args (list): List of option arguments.  Generally something like
                ``['-h', '--help']``.

        Keyword Args:
            dest (str): The destination name (variable).  Default: `args[0]`
            help (str): The help text for ``--help`` output (for that
                argument).
            action (str): Must support: ``['store', 'store_true',
                'store_false', 'store_const']``
            choices (list): A list of valid values that can be passed to an
                option whose action is ``store``.
            const (str): The value stored if ``action == 'store_const'``.
            default (str): The default value.

        Returns:
            None

        """
        pass    # pragma: nocover

    @abstractmethod
    def parse(self, *args: List[str]) -> object:
        """
        Parse the argument list (i.e. ``sys.argv``).  Can return any object as
        long as its' members contain those of the added arguments.  For
        example, if adding a ``-v/--version`` option that stores to the dest of
        ``version``, then the member must be callable as ``Object().version``.

        Args:
            args (list): A list of command line arguments

        Returns:
            object: A callable object whose members reprisent the available
            arguments

        """
        pass    # pragma: nocover


class ArgumentHandler(ArgumentInterface, Handler):

    """Argument handler implementation"""

    class Meta(Handler.Meta):
        pass    # pragma: nocover
