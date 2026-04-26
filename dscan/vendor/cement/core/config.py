"""Cement core config module."""

import os
from ..core import interface, handler
from ..utils.fs import abspath
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


def config_validator(klass, obj):
    """Validates a handler implementation against the IConfig interface."""
    members = [
        '_setup',
        'keys',
        'get_sections',
        'get_section_dict',
        'get',
        'set',
        'parse_file',
        'merge',
        'add_section',
        'has_section',
    ]
    interface.validate(IConfig, obj, members)


class IConfig(interface.Interface):

    """
    This class defines the Config Handler Interface.  Classes that
    implement this handler must provide the methods and attributes defined
    below.

    All implementations must provide sane 'default' functionality when
    instantiated with no arguments.  Meaning, it can and should accept
    optional parameters that alter how it functions, but can not require
    any parameters.  When the framework first initializes handlers it does
    not pass anything too them, though a handler can be instantiated first
    (with or without parameters) and then passed to 'CementApp()' already
    instantiated.

    Implementations do *not* subclass from interfaces.

    Usage:

    .. code-block:: python

        from cement.core import config

        class MyConfigHandler(config.CementConfigHandler):
            class Meta:
                interface = config.IConfig
                label = 'my_config_handler'
            ...

    """
    # pylint: disable=W0232, C0111, R0903
    class IMeta:

        """Interface meta-data."""
        label = 'config'
        """The string identifier of the interface."""

        validator = config_validator
        """The validator function."""

    # Must be provided by the implementation
    Meta = interface.Attribute('Handler Meta-data')

    def _setup(app_obj):
        """
        The _setup function is called during application initialization and
        must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object.
        :returns: None

        """

    def parse_file(file_path):
        """
        Parse config file settings from file_path.  Returns True if the file
        existed, and was parsed successfully.  Returns False otherwise.

        :param file_path: The path to the config file to parse.
        :returns: True if the file was parsed, False otherwise.
        :rtype: boolean

        """

    def keys(section):
        """
        Return a list of configuration keys from `section`.

        :param section: The config [section] to pull keys from.
        :returns: A list of keys in `section`.
        :rtype: list

        """

    def get_sections():
        """
        Return a list of configuration sections.  These are designated by a
        [block] label in a config file.

        :returns: A list of config sections.
        :rtype: list

        """

    def get_section_dict(section):
        """
        Return a dict of configuration parameters for [section].

        :param section: The config [section] to generate a dict from (using
            that section keys).
        :returns: A dictionary of the config section.
        :rtype: dict

        """

    def add_section(section):
        """
        Add a new section if it doesn't exist.

        :param section: The [section] label to create.
        :returns: None

        """

    def get(section, key):
        """
        Return a configuration value based on [section][key].  The return
        value type is unknown.

        :param section: The [section] of the configuration to pull key value
            from.
        :param key: The configuration key to get the value from.
        :returns: The value of the `key` in `section`.
        :rtype: Unknown

        """

    def set(section, key, value):
        """
        Set a configuration value based at [section][key].

        :param section: The [section] of the configuration to pull key value
            from.
        :param key: The configuration key to set the value at.
        :param value: The value to set.
        :returns: None

        """

    def merge(dict_obj, override=True):
        """
        Merges a dict object into the configuration.

        :param dict_obj: The dictionary to merge into the config
        :param override: Boolean.  Whether to override existing values.
            Default: True
        :returns: None
        """

    def has_section(section):
        """
        Returns whether or not the section exists.

        :param section: The section to test for.
        :returns: boolean

        """


class CementConfigHandler(handler.CementBaseHandler):

    """
    Base class that all Config Handlers should sub-class from.

    """
    class Meta:

        """
        Handler meta-data (can be passed as keyword arguments to the parent
        class).
        """

        label = None
        """The string identifier of the implementation."""

        interface = IConfig
        """The interface that this handler implements."""

    def __init__(self, *args, **kw):
        super(CementConfigHandler, self).__init__(*args, **kw)

    def _parse_file(self, file_path):
        """
        Parse a configuration file at `file_path` and store it.  This function
        must be provided by the handler implementation (that is sub-classing
        this).

        :param file_path: The file system path to the configuration file.
        :returns: boolean (True if file was read properly, False otherwise)

        """
        raise NotImplementedError

    def parse_file(self, file_path):
        """
        Ensure we are using the absolute/expanded path to `file_path`, and
        then call `_parse_file` to parse config file settings from it,
        overwriting existing config settings.  If the file does not exist,
        returns False.

        Developers sub-classing from here should generally override
        `_parse_file` which handles just the parsing of the file and leaving
        this function to wrap any checks/logging/etc.

        :param file_path: The file system path to the configuration file.
        :returns: boolean

        """
        file_path = abspath(file_path)
        if os.path.exists(file_path):
            LOG.debug("config file '%s' exists, loading settings..." %
                      file_path)
            return self._parse_file(file_path)
        else:
            LOG.debug("config file '%s' does not exist, skipping..." %
                      file_path)
            return False
