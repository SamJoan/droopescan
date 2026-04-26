"""JSON ConfigObj Framework Extension"""

import os
import json
from ..core import handler
from ..utils.misc import minimal_logger
from ..utils.fs import abspath
from ..ext.ext_configobj import ConfigObjConfigHandler

LOG = minimal_logger(__name__)


class JsonConfigObjConfigHandler(ConfigObjConfigHandler):

    """
    This class implements the :ref:`IConfig <cement.core.config>`
    interface, and provides the same functionality of
    :ref:`ConfigObjConfigHandler <cement.ext.ext_configobj>`
    but with JSON configuration files.

    **Note** This extension has an external dependency on `ConfigObj`.  You
    must include `configobj` in your application's dependencies as Cement
    explicitly does *not* include external dependencies for optional
    extensions.

    """

    class Meta:
        label = 'json_configobj'

    def __init__(self, *args, **kw):
        super(JsonConfigObjConfigHandler, self).__init__(*args, **kw)

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
    handler.register(JsonConfigObjConfigHandler)
