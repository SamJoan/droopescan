from cement.core import controller, foundation, backend
from cement.utils import test
from droopescan import DroopeScan
from mock import patch, MagicMock
from plugins.drupal import DrupalScanner
import common
import droopescan

class BaseTest(test.CementTestCase):
    app_class = DroopeScan
    base_url = ["--url", "http://example.com/"]

    def setUp(self):
        super(BaseTest, self).setUp()
        self.reset_backend()
        self.app = DroopeScan(argv=[],
            plugin_config_dir="./plugins.d",
            plugin_dir="./plugins")
        self.app.testing = True
        self.app.setup()

    def tearDown(self):
        self.app.close()

    def mock(self, plugin_label, method):
        m = MagicMock()
        setattr(backend.__handlers__['controller'][plugin_label], method, m)
        return m

    def add_argv(self, argv):
        """
        Concatenates list with self.app.argv.
        """
        self.app._meta.argv += argv

class DroopeScanTest(BaseTest):
    """
        This class should contain tests which encompass all CMSs
    """

    @test.raises(RuntimeError)
    def test_errors_when_no_module(self):
        self.app.run()

    @test.raises(RuntimeError)
    def test_errors_when_no_url(self):
        self.add_argv(["drupal"])
        self.app.run()

    @test.raises(RuntimeError)
    def test_errors_when_invalid_url(self):
        self.add_argv(["drupal"])
        self.add_argv(["--url", "invalidurl"])
        self.app.run()

    @test.raises(RuntimeError)
    def test_errors_when_no_enumerate(self):
        # add url to make sure that it does not error because of the url
        self.add_argv(["drupal"])
        self.add_argv(self.base_url)
        self.app.run()

    @test.raises(RuntimeError)
    def test_errors_when_invalid_enumerate(self):
        self.add_argv(["drupal"])
        self.add_argv(self.base_url + ["-e", 'z'])
        self.app.run()

    def test_calls_plugin(self):
        self.add_argv(["drupal"])
        self.add_argv(self.base_url + ["-e", 'p'])

        m = self.mock('drupalscanner', 'enumerate_plugins')

        self.app.run()
        assert m.called, "enumerate_plugins should have been called given the arguments"

class DrupalTest(BaseTest):
    """
        This class should contain tests specific to Drupal
    """

    def setUp(self):
        super(DrupalTest, self).setUp()
        self.add_argv(["drupal"])


