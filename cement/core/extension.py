"""Cement core extensions module."""

import sys
from ..core import exc, interface, handler
from ..utils.misc import minimal_logger

if sys.version_info[0] >= 3:
    from importlib import reload  # pragma: no cover

LOG = minimal_logger(__name__)


def extension_validator(klass, obj):
    """
    Validates an handler implementation against the IExtension interface.

    """
    members = [
        '_setup',
        'load_extension',
        'load_extensions',
        'get_loaded_extensions',
    ]
    interface.validate(IExtension, obj, members)


class IExtension(interface.Interface):

    """
    This class defines the Extension Handler Interface.  Classes that
    implement this handler must provide the methods and attributes defined
    below.

    Implementations do *not* subclass from interfaces.

    Usage:

    .. code-block:: python

        from cement.core import extension

        class MyExtensionHandler(object):
            class Meta:
                interface = extension.IExtension
                label = 'my_extension_handler'
            ...

    """

    # pylint: disable=W0232, C0111, R0903
    class IMeta:

        """Interface meta-data."""

        label = 'extension'
        """The string identifier of the interface."""

        validator = extension_validator
        """The interface validator function."""

    # Must be provided by the implementation
    Meta = interface.Attribute('Handler Meta-data class')

    def _setup(app_obj):
        """
        The _setup function is called during application initialization and
        must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object.
        :returns: None

        """

    def load_extension(self, ext_module):
        """
        Load an extension whose module is 'ext_module'.  For example,
        'cement.ext.ext_configobj'.

        :param ext_module: The name of the extension to load.
        :type ext_module: str

        """

    def load_extensions(self, ext_list):
        """
        Load all extensions from ext_list.

        :param ext_list: A list of extension modules to load.  For example:
            ``['cement.ext.ext_configobj', 'cement.ext.ext_logging']``

        :type ext_list: list

        """


class CementExtensionHandler(handler.CementBaseHandler):

    class Meta:

        """
        Handler meta-data (can be passed as keyword arguments to the parent
        class).
        """

        interface = IExtension
        """The interface that this class implements."""

        label = 'cement'
        """The string identifier of the handler."""

    def __init__(self, **kw):
        """
        This is an implementation of the IExtentionHandler interface.  It
        handles loading framework extensions.

        """
        super(CementExtensionHandler, self).__init__(**kw)
        self.app = None
        self._loaded_extensions = []

    def get_loaded_extensions(self):
        """Returns list of loaded extensions."""
        return self._loaded_extensions

    def load_extension(self, ext_module):
        """
        Given an extension module name, load or in other-words 'import' the
        extension.

        :param ext_module: The extension module name.  For example:
            'cement.ext.ext_logging'.
        :type ext_module: str
        :raises: cement.core.exc.FrameworkError

        """
        # If its not a full module path then preppend our default path
        if ext_module.find('.') == -1:
            ext_module = 'cement.ext.ext_%s' % ext_module

        if ext_module in self._loaded_extensions:
            LOG.debug("framework extension '%s' already loaded" % ext_module)
            return

        LOG.debug("loading the '%s' framework extension" % ext_module)
        try:
            if ext_module not in sys.modules:
                __import__(ext_module, globals(), locals(), [], 0)

            if hasattr(sys.modules[ext_module], 'load'):
                sys.modules[ext_module].load(self.app)

            if ext_module not in self._loaded_extensions:
                self._loaded_extensions.append(ext_module)

        except ImportError as e:
            raise exc.FrameworkError(e.args[0])

    def load_extensions(self, ext_list):
        """
        Given a list of extension modules, iterate over the list and pass
        individually to self.load_extension().

        :param ext_list: A list of extension modules.
        :type ext_list: list

        """
        for ext in ext_list:
            self.load_extension(ext)
