"""
Cement print extension module.
"""

from __future__ import annotations
from typing import Any, Dict, Union, TYPE_CHECKING
from ..core import output
from ..utils.misc import minimal_logger

if TYPE_CHECKING:
    from ..core.foundation import App  # pragma: nocover

LOG = minimal_logger(__name__)


def extend_print(app: App) -> None:
    def _print(text: str) -> None:
        app.render({'out': text}, handler='print')
    app.extend('print', _print)


class PrintOutputHandler(output.OutputHandler):

    """
    This class implements the :ref:`Output <cement.core.output>` Handler
    interface.  It takes a dict and only prints out the ``out`` key. It is
    primarily used by the ``app.print()`` extended function in order to replace
    ``print()`` so that framework features like ``pre_render`` and
    ``post_render`` hooks are honored. Please see the developer documentation
    on :cement:`Output Handling <dev/output>`.

    """
    class Meta(output.OutputHandler.Meta):

        """Handler meta-data"""

        label = 'print'
        """The string identifier of this handler."""

        #: Whether or not to include ``json`` as an available choice
        #: to override the ``output_handler`` via command line options.
        overridable = False

    _meta: Meta  # type: ignore

    def render(self, data: Dict[str, Any], *args: Any, **kw: Any) -> Union[str, None]:
        """
        Take a data dictionary and render only the ``out`` key as text output.
        Note that the template option is received here per the interface,
        however this handler just ignores it.

        Args:
            data (dict): The data dictionary to render.

        Returns:
            str: A text string.

        """
        if 'out' in data.keys():
            LOG.debug(f"rendering content as text via {self.__module__}")
            return data['out'] + '\n'  # type: ignore
        else:
            LOG.debug("no 'out' key found in data dict. "
                      "not rendering content via %s" % self.__module__)
            return None


class PrintDictOutputHandler(output.OutputHandler):

    """
    This class implements the :ref:`Output <cement.core.output>` Handler
    interface.  It is intended primarily for development where printing out a
    string reprisentation of the data dictionary would be useful.  Please see
    the developer documentation on :cement:`Output Handling <dev/output>`.

    """
    class Meta(output.OutputHandler.Meta):

        """Handler meta-data"""

        label = 'print_dict'
        """The string identifier of this handler."""

        #: Whether or not to include ``json`` as an available choice
        #: to override the ``output_handler`` via command line options.
        overridable = False

    _meta: Meta  # type: ignore

    def render(self, data: Dict[str, Any], *args: Any, **kw: Any) -> str:
        """
        Take a data dictionary and render it as text output.  Note that the
        template option is received here per the interface, however this
        handler just ignores it.

        Args:
            data (dict): The data dictionary to render.

        Returns:
            str: A text string.

        """
        LOG.debug(f"rendering content as text via {self.__module__}")
        out = ''
        for key, val in data.items():
            out = out + f'{key}: {val}\n'

        return out


def load(app: App) -> None:
    app.handler.register(PrintDictOutputHandler)
    app.handler.register(PrintOutputHandler)
    app.hook.register('pre_argument_parsing', extend_print)
