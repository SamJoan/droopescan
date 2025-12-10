"""
Cement Tabulate extension module.

**Note** This extension has an external dependency on ``tabulate``. Cement
explicitly does **not** include external dependencies for optional
extensions.

* In Cement ``>=3.0.8`` you must include ``cement[tabulate]`` in your
  applications dependencies.
* In Cement ``<3.0.8`` you must include ``tabulate`` in your applications
  dependencies.
"""

from __future__ import annotations
from tabulate import tabulate  # type: ignore
from typing import Any, List, Dict, TYPE_CHECKING
from ..core import output
from ..utils.misc import minimal_logger

if TYPE_CHECKING:
    from ..core.foundation import App  # pragma: nocover

LOG = minimal_logger(__name__)


class TabulateOutputHandler(output.OutputHandler):

    """
    This class implements the :ref:`Output <cement.core.output>` Handler
    interface.  It provides tabularized text output using the
    `Tabulate <https://pypi.python.org/pypi/tabulate>`_ module.  Please
    see the developer documentation on
    :cement:`Output Handling <dev/output>`.
    """

    class Meta(output.OutputHandler.Meta):

        """Handler meta-data."""

        label = 'tabulate'

        #: Whether or not to pad the output with an extra pre/post '\n'
        padding = True

        #: Default template format.  See the ``tabulate`` documentation for
        #: all supported template formats.
        format = 'orgtbl'

        #: Default headers to use.
        headers: List[str] = []

        #: Default alignment for string columns.  See the ``tabulate``
        #: documentation for all supported ``stralign`` options.
        string_alignment = 'left'

        #: Default alignment for numeric columns.  See the ``tabulate``
        #: documentation for all supported ``numalign`` options.
        numeric_alignment = 'decimal'

        #: String format to use for float values.
        float_format = 'g'

        #: Default replacement for missing value.
        missing_value = ''

        #: Whether or not to include ``tabulate`` as an available to choice
        #: to override the ``output_handler`` via command line options.
        overridable = False

    _meta: Meta  # type: ignore

    def render(self, data: Dict[str, Any], **kw: Any) -> str:
        """
        Take a data dictionary and render it into a table.  Additional
        keyword arguments are passed directly to ``tabulate.tabulate``.

        Args:
            data_dict (dict): The data dictionary to render.

        Returns:
            str: The rendered template text

        """
        headers = kw.get('headers', self._meta.headers)

        out = tabulate(data, headers,
                       tablefmt=kw.get('tablefmt', self._meta.format),
                       stralign=kw.get(
                           'stralign', self._meta.string_alignment),
                       numalign=kw.get(
                           'numalign', self._meta.numeric_alignment),
                       missingval=kw.get(
                           'missingval', self._meta.missing_value),
                       floatfmt=kw.get('floatfmt', self._meta.float_format),
                       )
        out = out + '\n'

        if self._meta.padding is True:
            out = '\n' + out + '\n'

        return out  # type: ignore


def load(app: App) -> None:
    app.handler.register(TabulateOutputHandler)
