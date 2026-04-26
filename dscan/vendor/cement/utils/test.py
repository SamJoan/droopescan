"""Cement testing utilities."""

import unittest
from tempfile import mkstemp, mkdtemp
from ..core import backend, foundation
from ..utils.misc import rando

# shortcuts
from nose import SkipTest
from nose.tools import ok_ as ok
from nose.tools import eq_ as eq
from nose.tools import raises
from nose.plugins.attrib import attr


class TestApp(foundation.CementApp):

    """
    Basic CementApp for generic testing.

    """
    class Meta:
        label = "app-%s" % rando()[:12]
        config_files = []
        argv = []
        base_controller = None
        arguments = []
        exit_on_close = False


class CementTestCase(unittest.TestCase):

    """
    A sub-class of unittest.TestCase.

    """

    app_class = TestApp
    """The test class that is used by self.make_app to create an app."""

    def __init__(self, *args, **kw):
        super(CementTestCase, self).__init__(*args, **kw)

    def setUp(self):
        """
        Sets up self.app with a generic TestApp().  Also resets the backend
        hooks and handlers so that everytime an app is created it is setup
        clean each time.

        """
        self.app = self.make_app()
        _, self.tmp_file = mkstemp()
        self.tmp_dir = mkdtemp()

    def make_app(self, *args, **kw):
        """
        Create a generic app using TestApp.  Arguments and Keyword Arguments
        are passed to the app.

        """
        self.reset_backend()
        return self.app_class(*args, **kw)

    def reset_backend(self):
        """
        Remove all registered hooks and handlers from the backend.

        """
        for _handler in backend.__handlers__.copy():
            del backend.__handlers__[_handler]
        for _hook in backend.__hooks__.copy():
            del backend.__hooks__[_hook]

    def ok(self, expr, msg=None):
        """Shorthand for assert."""
        return ok(expr, msg)

    def eq(self, a, b, msg=None):
        """Shorthand for 'assert a == b, "%r != %r" % (a, b)'. """
        return eq(a, b, msg)

# The following are for internal, Cement unit testing only


@attr('core')
class CementCoreTestCase(CementTestCase):
    pass


@attr('ext')
class CementExtTestCase(CementTestCase):
    pass
