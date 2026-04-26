"""JSON Framework Extension"""

import sys
import json
from ..core import output, backend, hook, handler
from ..utils.misc import minimal_logger
from ..ext.ext_configparser import ConfigParserConfigHandler

LOG = minimal_logger(__name__)


def suppress_output_before_run(app):
    """
    This is a ``post_argument_parsing`` hook that suppresses console output if
    the ``JsonOutputHandler`` is triggered via command line.

    :param app: The application object.

    """
    if not hasattr(app.pargs, 'output_handler_override'):
        return
    elif app.pargs.output_handler_override == 'json':
        app._suppress_output()


def unsuppress_output_before_render(app, data):
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


def suppress_output_after_render(app, out_text):
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


class JsonOutputHandler(output.CementOutputHandler):

    """
    This class implements the :ref:`IOutput <cement.core.output>`
    interface.  It provides JSON output from a data dictionary using the
    `json <http://docs.python.org/library/json.html>`_ module of the standard
    library.  Please see the developer documentation on
    :ref:`Output Handling <dev_output_handling>`.

    Note: By default, Cement adds the ``-o`` command line option to allow the
    end user to override the output handler.  For example: passing ``-o json``
    will override the default output handler and set it to
    ``JsonOutputHandler``.  See ``CementApp.Meta.handler_override_options``.

    This extension forces Cement to suppress console output until
    ``app.render`` is called (keeping the output pure JSON).  If
    troubleshooting issues, you will need to pass the ``--debug`` option in
    order to unsuppress output and see what's happening.

    """
    class Meta:

        """Handler meta-data"""

        interface = output.IOutput
        """The interface this class implements."""

        label = 'json'
        """The string identifier of this handler."""

        overridable = True

    def __init__(self, *args, **kw):
        super(JsonOutputHandler, self).__init__(*args, **kw)

    def render(self, data_dict, template=None):
        """
        Take a data dictionary and render it as Json output.  Note that the
        template option is received here per the interface, however this
        handler just ignores it.

        :param data_dict: The data dictionary to render.
        :param template: This option is completely ignored.
        :returns: A JSON encoded string.
        :rtype: str

        """
        LOG.debug("rendering output as Json via %s" % self.__module__)
        return json.dumps(data_dict)


class JsonConfigHandler(ConfigParserConfigHandler):

    """
    This class implements the :ref:`IConfig <cement.core.config>`
    interface, and provides the same functionality of
    :ref:`ConfigParserConfigHandler <cement.ext.ext_configparser>`
    but with JSON configuration files.

    """
    class Meta:
        label = 'json'

    def __init__(self, *args, **kw):
        super(JsonConfigHandler, self).__init__(*args, **kw)

    def _parse_file(self, file_path):
        """
        Parse JSON configuration file settings from file_path, overwriting
        existing config settings.  If the file does not exist, returns False.

        :param file_path: The file system path to the JSON configuration file.
        :returns: boolean

        """
        self.merge(json.load(open(file_path)))

        # FIX ME: Should check that file was read properly, however if not it
        # will likely raise an exception anyhow.
        return True


def load(app):
    hook.register('post_argument_parsing', suppress_output_before_run)
    hook.register('pre_render', unsuppress_output_before_render)
    hook.register('post_render', suppress_output_after_render)
    handler.register(JsonOutputHandler)
    handler.register(JsonConfigHandler)
