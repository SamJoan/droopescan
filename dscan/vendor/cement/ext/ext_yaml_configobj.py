"""YAML ConfigObj Framework Extension"""

import os
import yaml
from ..core import handler
from ..utils.misc import minimal_logger
from ..utils.fs import abspath
from ..ext.ext_configobj import ConfigObjConfigHandler

LOG = minimal_logger(__name__)


class YamlConfigObjConfigHandler(ConfigObjConfigHandler):

    """
    This class implements the :ref:`IConfig <cement.core.config>`
    interface, and provides the same functionality of
    :ref:`ConfigObjConfigHandler <cement.ext.ext_configobj>`
    but with YAML configuration files.  See
    `pyYAML <http://pyyaml.org/wiki/PyYAMLDocumentation>`_ for more
    information on pyYAML

    **Note** This extension has an external dependency on `pyYAML` and
    `ConfigObj`.  You must include `pyYAML` and `configobj` in your
    application's dependencies as Cement explicitly does *not* include
    external dependencies for optional extensions.

    """

    class Meta:
        label = 'yaml_configobj'

    def __init__(self, *args, **kw):
        super(YamlConfigObjConfigHandler, self).__init__(*args, **kw)

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
    handler.register(YamlConfigObjConfigHandler)
