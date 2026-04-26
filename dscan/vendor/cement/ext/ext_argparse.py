"""ArgParse Framework Extension"""

from argparse import ArgumentParser
from ..core import backend, arg, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class ArgParseArgumentHandler(arg.CementArgumentHandler, ArgumentParser):

    """
    This class implements the :ref:`IArgument <cement.core.arg>`
    interface, and sub-classes from `argparse.ArgumentParser
    <http://docs.python.org/dev/library/argparse.html>`_.
    Please reference the argparse documentation for full usage of the
    class.

    Arguments and Keyword arguments are passed directly to ArgumentParser
    on initialization.
    """

    class Meta:

        """Handler meta-data."""

        interface = arg.IArgument
        """The interface that this class implements."""

        label = 'argparse'
        """The string identifier of the handler."""

    def __init__(self, *args, **kw):
        super(ArgParseArgumentHandler, self).__init__(*args, **kw)
        self.config = None

    def parse(self, arg_list):
        """
        Parse a list of arguments, and return them as an object.  Meaning an
        argument name of 'foo' will be stored as parsed_args.foo.

        :param arg_list: A list of arguments (generally sys.argv) to be
         parsed.
        :returns: object whose members are the arguments parsed.

        """
        return self.parse_args(arg_list)

    def add_argument(self, *args, **kw):
        """
        Add an argument to the parser.  Arguments and keyword arguments are
        passed directly to ArgumentParser.add_argument().

        """
        return super(ArgumentParser, self).add_argument(*args, **kw)


def load(app):
    handler.register(ArgParseArgumentHandler)
