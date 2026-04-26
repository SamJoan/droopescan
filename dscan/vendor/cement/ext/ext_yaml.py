"""YAML Framework Extension"""

import os
import sys
import yaml
from ..core import backend, output, hook, handler, config
from ..utils.misc import minimal_logger
from ..ext.ext_configparser import ConfigParserConfigHandler

LOG = minimal_logger(__name__)


def suppress_output_before_run(app):
    """
    This is a ``post_argument_parsing`` hook that suppresses console output if
    the ``YamlOutputHandler`` is triggered via command line.

    :param app: The application object.

    """
    if not hasattr(app.pargs, 'output_handler_override'):
        return
    elif app.pargs.output_handler_override == 'yaml':
        app._suppress_output()


def unsuppress_output_before_render(app, data):
    """
    This is a ``pre_render`` that unsuppresses console output if
    the ``YamlOutputHandler`` is triggered via command line so that the YAML
    is the only thing in the output.

    :param app: The application object.

    """
    if not hasattr(app.pargs, 'output_handler_override'):
        return
    elif app.pargs.output_handler_override == 'yaml':
        app._unsuppress_output()


def suppress_output_after_render(app, out_text):
    """
    This is a ``post_render`` hook that suppresses console output again after
    rendering, only if the ``YamlOutputHandler`` is triggered via command
    line.

    :param app: The application object.

    """
    if not hasattr(app.pargs, 'output_handler_override'):
        return
    elif app.pargs.output_handler_override == 'yaml':
        app._suppress_output()


class YamlOutputHandler(output.CementOutputHandler):

    """
    This class implements the :ref:`IOutput <cement.core.output>`
    interface.  It provides YAML output from a data dictionary and uses
    `pyYAML <http://pyyaml.org/wiki/PyYAMLDocumentation>`_ to dump it to
    STDOUT.  Please see the developer documentation on
    :ref:`Output Handling <dev_output_handling>`.

    Note: By default, Cement adds the ``-o`` command line option to allow the
    end user to override the output handler.  For example: passing ``-o yaml``
    will override the default output handler and set it to
    ``YamlOutputHandler``.  See ``CementApp.Meta.handler_override_options``.

    This extension forces Cement to suppress console output until
    ``app.render`` is called (keeping the output pure YAML).  If
    troubleshooting issues, you will need to pass the ``--debug`` option in
    order to unsuppress output and see what's happening.

    """
    class Meta:
        interface = output.IOutput
        label = 'yaml'
        overridable = True

    def __init__(self, *args, **kw):
        super(YamlOutputHandler, self).__init__(*args, **kw)
        self.config = None

    def _setup(self, app_obj):
        self.app = app_obj

    def render(self, data_dict, template=None):
        """
        Take a data dictionary and render it as Yaml output.  Note that the
        template option is received here per the interface, however this
        handler just ignores it.

        :param data_dict: The data dictionary to render.
        :param template: This option is completely ignored.
        :returns: A Yaml encoded string.
        :rtype: str

        """
        LOG.debug("rendering output as Yaml via %s" % self.__module__)
        sys.stdout = backend.__saved_stdout__
        sys.stderr = backend.__saved_stderr__
        return yaml.dump(data_dict)


class YamlConfigHandler(ConfigParserConfigHandler):

    """
    This class implements the :ref:`IConfig <cement.core.config>`
    interface, and provides the same functionality of
    :ref:`ConfigParserConfigHandler <cement.ext.ext_configparser>`
    but with YAML configuration files.  See
    `pyYAML <http://pyyaml.org/wiki/PyYAMLDocumentation>`_ for more
    information on pyYAML.

    **Note** This extension has an external dependency on `pyYAML`.  You must
    include `pyYAML` in your application's dependencies as Cement explicitly
    does *not* include external dependencies for optional extensions.

    """
    class Meta:
        label = 'yaml'

    def __init__(self, *args, **kw):
        super(YamlConfigHandler, self).__init__(*args, **kw)

    def _parse_file(self, file_path):
        """
        Parse YAML configuration file settings from file_path, overwriting
        existing config settings.  If the file does not exist, returns False.

        :param file_path: The file system path to the YAML configuration file.
        :returns: boolean

        """
        self.merge(yaml.load(open(file_path)))

        # FIX ME: Should check that file was read properly, however if not it
        # will likely raise an exception anyhow.
        return True


def load(app):
    hook.register('post_argument_parsing', suppress_output_before_run)
    hook.register('pre_render', unsuppress_output_before_render)
    hook.register('post_render', suppress_output_after_render)
    handler.register(YamlOutputHandler)
    handler.register(YamlConfigHandler)
