"""
Cement json extension module.
"""

from __future__ import annotations
from typing import Any, Dict, TYPE_CHECKING
from ..core import output
from ..utils.misc import minimal_logger
from ..ext.ext_configparser import ConfigParserConfigHandler

if TYPE_CHECKING:
    from ..core.foundation import App  # pragma: nocover

LOG = minimal_logger(__name__)


def suppress_output_before_run(app: App) -> None:
    """
    This is a ``post_argument_parsing`` hook that suppresses console output if
    the ``JsonOutputHandler`` is triggered via command line.

    :param app: The application object.

    """
    if not hasattr(app.pargs, 'output_handler_override'):
        return
    elif app.pargs.output_handler_override == 'json':
        app._suppress_output()


def unsuppress_output_before_render(app: App, data: Any) -> None:
    """
    This is a ``pre_render`` that unsuppresses console output if
    the ``JsonOutputHandler`` is triggered via command line so that the JSON
    is the only thing in the output.

    :param app: The application object.

    """
    if not hasattr(app.pargs, 'output_handler_override'):
        return
    elif app.pargs.output_handler_override == 'json':
        app._unsuppress_output()


def suppress_output_after_render(app: App, out_text: str) -> None:
    """
    This is a ``post_render`` hook that suppresses console output again after
    rendering, only if the ``JsonOutputHandler`` is triggered via command
    line.

    :param app: The application object.

    """
    if not hasattr(app.pargs, 'output_handler_override'):
        return
    elif app.pargs.output_handler_override == 'json':
        app._suppress_output()


class JsonOutputHandler(output.OutputHandler):

    """
    This class implements the :ref:`Output <cement.core.output>` Handler
    interface.  It provides JSON output from a data dictionary using the
    `json <http://docs.python.org/library/json.html>`_ module of the standard
    library.  Please see the developer documentation on
    :cement:`Output Handling <dev/output>`.

    This handler forces Cement to suppress console output until
    ``app.render`` is called (keeping the output pure JSON).  If
    troubleshooting issues, you will need to pass the ``--debug`` option in
    order to unsuppress output and see what's happening.

    """
    class Meta(output.OutputHandler.Meta):

        """Handler meta-data"""

        label = 'json'
        """The string identifier of this handler."""

        #: Whether or not to include ``json`` as an available choice
        #: to override the ``output_handler`` via command line options.
        overridable = False

        #: Backend JSON library module to use (`json`, `ujson`)
        json_module = 'json'

    _meta: Meta  # type: ignore

    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)
        self._json = None

    def _setup(self, app: App) -> None:
        super()._setup(app)
        self._json = __import__(self._meta.json_module,         # type: ignore
                                globals(), locals(), [], 0)

    def render(self, data: Dict[str, Any], template: str = None, **kw: Any) -> str:  # type: ignore
        """
        Take a data dictionary and render it as Json output.  Note that the
        template option is received here per the interface, however this
        handler just ignores it.  Additional keyword arguments passed to
        ``json.dumps()``.

        Args:
            data (dict): The data dictionary to render.

        Keyword Args:
            template: This option is completely ignored.

        Returns:
            str: A JSON encoded string.

        """
        LOG.debug(f"rendering output as Json via {self.__module__}")
        return self._json.dumps(data, **kw)  # type: ignore


class JsonConfigHandler(ConfigParserConfigHandler):

    """
    This class implements the :ref:`Config <cement.core.config>` Handler
    interface, and provides the same functionality of
    :ref:`ConfigParserConfigHandler <cement.ext.ext_configparser>`
    but with JSON configuration files.

    """
    class Meta(ConfigParserConfigHandler.Meta):

        """Handler meta-data."""

        label = 'json'

        #: Backend JSON library module to use (`json`, `ujson`).
        json_module = 'json'

    _meta: Meta  # type: ignore

    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)
        self._json = None

    def _setup(self, app: App) -> None:
        super()._setup(app)
        self._json = __import__(self._meta.json_module,         # type: ignore
                                globals(), locals(), [], 0)

    def _parse_file(self, file_path: str) -> bool:
        """
        Parse JSON configuration file settings from file_path, overwriting
        existing config settings.  If the file does not exist, returns False.

        Args:
            file_path (str): The file system path to the JSON configuration
            file.

        Returns:
            bool

        """
        with open(file_path, 'r') as f:
            content = f.read()
            if content is not None and len(content) > 0:
                self.merge(self._json.loads(content))

        return True


def load(app: App) -> None:
    app.hook.register('post_argument_parsing', suppress_output_before_run)
    app.hook.register('pre_render', unsuppress_output_before_render)
    app.hook.register('post_render', suppress_output_after_render)
    app.handler.register(JsonOutputHandler)
    app.handler.register(JsonConfigHandler)
