"""ConfigObj Framework Extension."""

import os
import sys
from ..core import config, exc, handler
from ..utils.misc import minimal_logger
from configobj import ConfigObj

LOG = minimal_logger(__name__)


class ConfigObjConfigHandler(config.CementConfigHandler, ConfigObj):

    """
    This class implements the :ref:`IConfig <cement.core.config>`
    interface, and sub-classes from `configobj.ConfigObj
    <http://www.voidspace.org.uk/python/configobj.html>`_,
    which is an external library and not included with Python. Please
    reference the ConfigObj documentation for full usage of the class.

    Arguments and keyword arguments are passed directly to ConfigObj
    on initialization.

    """
    class Meta:
        interface = config.IConfig
        label = 'configobj'

    def __init__(self, *args, **kw):
        super(ConfigObjConfigHandler, self).__init__(*args, **kw)
        self.app = None

    def _setup(self, app_obj):
        self.app = app_obj

    def get_sections(self):
        """
        Return a list of [section] that exist in the configuration.

        :returns: list
        """
        return self.sections

    def get_section_dict(self, section):
        """
        Return a dict representation of a section.

        :param section: The section of the configuration.
         I.e. ``[block_section]``
        :returns: dict

        """
        dict_obj = dict()
        for key in self.keys(section):
            dict_obj[key] = self.get(section, key)
        return dict_obj

    def _parse_file(self, file_path):
        """
        Parse a configuration file at `file_path` and store it.

        :param file_path: The file system path to the configuration file.
        :returns: boolean (True if file was read properly, False otherwise)

        """
        _c = ConfigObj(file_path)
        self.merge(_c.dict())

        # FIX ME: Should check that file was read properly, however if not it
        # will likely raise an exception anyhow.
        return True

    def keys(self, section):
        """
        Return a list of keys for a given section.

        :param section: The configuration [section].

        """
        return self[section].keys()

    def get(self, section, key):
        """
        Get a value for a given key under section.

        :param section: The configuration [section].
        :param key: The configuration key under the section.
        :returns: unknown (the value of the key)

        """
        return self[section][key]

    def set(self, section, key, value):
        """
        Set a configuration key value under [section].

        :param section: The configuration [section].
        :param key: The configuration key under the section.
        :param value: The value to set the key to.
        :returns: None
        """
        self[section][key] = value

    def has_section(self, section):
        """
        Return True/False whether the configuration [section] exists.

        :param section: The section to check for.
        :returns: bool

        """
        if section in self.get_sections():
            return True
        else:
            return False

    def add_section(self, section):
        """
        Add a section to the configuration.

        :param section: The configuration [section] to add.

        """
        if not self.has_section(section):
            self[section] = dict()

    def merge(self, dict_obj, override=True):
        """
        Merge a dictionary into our config.  If override is True then
        existing config values are overridden by those passed in.

        :param dict_obj: A dictionary of configuration keys/values to merge
         into our existing config (self).
        :param override: Whether or not to override existing values in the
         config.
        :returns: None

        """
        for section in list(dict_obj.keys()):
            if type(dict_obj[section]) == dict:
                if section not in self.get_sections():
                    self.add_section(section)

                for key in list(dict_obj[section].keys()):
                    if override:
                        self.set(section, key, dict_obj[section][key])
                    else:
                        # only set it if the key doesn't exist
                        if key not in self.keys(section):
                            self.set(section, key, dict_obj[section][key])

                # we don't support nested config blocks, so no need to go
                # further down to more nested dicts.


def load(app):
    handler.register(ConfigObjConfigHandler)
