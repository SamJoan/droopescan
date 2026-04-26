"""Cement core output module."""

import os
import sys
import pkgutil
from ..core import backend, exc, interface, handler
from ..utils.misc import minimal_logger
from ..utils import fs

LOG = minimal_logger(__name__)


def output_validator(klass, obj):
    """Validates an handler implementation against the IOutput interface."""

    members = [
        '_setup',
        'render',
    ]
    interface.validate(IOutput, obj, members)


class IOutput(interface.Interface):

    """
    This class defines the Output Handler Interface.  Classes that
    implement this handler must provide the methods and attributes defined
    below.

    Implementations do *not* subclass from interfaces.

    Usage:

    .. code-block:: python

        from cement.core import output

        class MyOutputHandler(object):
            class Meta:
                interface = output.IOutput
                label = 'my_output_handler'
            ...

    """
    # pylint: disable=W0232, C0111, R0903
    class IMeta:

        """Interface meta-data."""

        label = 'output'
        """The string identifier of the interface."""

        validator = output_validator
        """The interface validator function."""

    # Must be provided by the implementation
    Meta = interface.Attribute('Handler meta-data')

    def _setup(app_obj):
        """
        The _setup function is called during application initialization and
        must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object.

        """

    def render(data_dict):
        """
        Render the data_dict into output in some fashion.

        :param data_dict: The dictionary whose data we need to render into
            output.
        :returns: string or unicode string or None

        """


class CementOutputHandler(handler.CementBaseHandler):

    """
    Base class that all Output Handlers should sub-class from.

    """
    class Meta:

        """
        Handler meta-data (can be passed as keyword arguments to the parent
        class).
        """

        label = None
        """The string identifier of this handler."""

        interface = IOutput
        """The interface that this class implements."""

    def __init__(self, *args, **kw):
        super(CementOutputHandler, self).__init__(*args, **kw)


class TemplateOutputHandler(CementOutputHandler):

    """
    Base class for template base output handlers.

    """

    def _load_template_from_file(self, template_path):
        for template_dir in self.app._meta.template_dirs:
            template_prefix = template_dir.rstrip('/')
            template_path = template_path.lstrip('/')
            full_path = fs.abspath(os.path.join(template_prefix,
                                                template_path))
            LOG.debug("attemping to load output template from file %s" %
                      full_path)
            if os.path.exists(full_path):
                content = open(full_path, 'r').read()
                LOG.debug("loaded output template from file %s" %
                          full_path)
                return content
            else:
                LOG.debug("output template file %s does not exist" %
                          full_path)
                continue

        return None

    def _load_template_from_module(self, template_path):
        template_module = self.app._meta.template_module
        template_path = template_path.lstrip('/')

        LOG.debug("attemping to load output template '%s' from module %s" %
                  (template_path, template_module))

        # see if the module exists first
        if template_module not in sys.modules:
            try:
                __import__(template_module, globals(), locals(), [], 0)
            except ImportError as e:
                LOG.debug("unable to import template module '%s'."
                          % template_module)
                return None

        # get the template content
        try:
            content = pkgutil.get_data(template_module, template_path)
            LOG.debug("loaded output template '%s' from module %s" %
                      (template_path, template_module))
            return content
        except IOError as e:
            LOG.debug("output template '%s' does not exist in module %s" %
                      (template_path, template_module))
            return None

    def load_template(self, template_path):
        """
        Loads a template file first from ``self.app._meta.template_dirs`` and
        secondly from ``self.app._meta.template_module``.  The
        ``template_dirs`` have presedence.

        :param template_path: The secondary path of the template **after**
            either ``template_module`` or ``template_dirs`` prefix (set via
            ``CementApp.Meta``)
        :returns: The content of the template (str)
        :raises: FrameworkError if the template does not exist in either the
            ``template_module`` or ``template_dirs``.
        """
        if not template_path:
            raise exc.FrameworkError("Invalid template path '%s'." %
                                     template_path)

        # first attempt to load from file
        content = self._load_template_from_file(template_path)
        if content is None:
            # second attempt to load from module
            content = self._load_template_from_module(template_path)

        # if content is None, that means we didn't find a template file in
        # either and that is an exception
        if content is not None:
            return content
        else:
            raise exc.FrameworkError("Could not locate template: %s" %
                                     template_path)
