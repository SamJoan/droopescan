from cement.core import controller, foundation, backend
from cement.utils import test
from droopescan import DroopeScan
from plugins.drupal import DrupalScanner
from plugins.drupal import DrupalScanner
from mock import patch, MagicMock
import requests
import responses

def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

class BaseTest(test.CementTestCase):
    app_class = DroopeScan
    scanner = None

    base_url = "http://example.com/"

    param_base_url = ["--url", base_url]
    param_plugins = param_base_url + ["-e", 'p']

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

    def mock_controller(self, plugin_label, method, return_value = None):
        """
            Mocks controller by label. Can only be used to test controllers
            that get instantiated automatically by cement.
        """
        m = MagicMock()
        if return_value:
            m.return_value = return_value

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
        self.add_argv(self.param_base_url)
        self.app.run()

    @test.raises(RuntimeError)
    def test_errors_when_invalid_enumerate(self):
        self.add_argv(["drupal"])
        self.add_argv(self.param_base_url + ["-e", 'z'])
        self.app.run()

    def test_calls_plugin(self):
        self.add_argv(["drupal"])
        self.add_argv(self.param_plugins)

        m = self.mock_controller('drupalscanner', 'enumerate_plugins')

        self.app.run()
        assert m.called, "enumerate_plugins should have been called given the arguments"

class DrupalTest(BaseTest):
    """
        This class should contain tests specific to Drupal
    """

    def setUp(self):
        super(DrupalTest, self).setUp()
        self.add_argv(["drupal"])
        self.scanner = DrupalScanner()

    @patch.object(DrupalScanner, 'plugins_get', return_value=["nonexistant1",
        "nonexistant2", "supermodule"])
    @responses.activate
    def test_returns_list_of_plugins(self, m):
        responses.add(responses.GET,
                "%ssites/all/modules/supermodule/" % self.base_url,
                body='403', status=403)
        responses.add(responses.GET,
                "%ssites/all/modules/nonexistant1/" % self.base_url,
                body='200', status=200)
        responses.add(responses.GET,
                "%ssites/all/modules/nonexistant2/" % self.base_url,
                body='200', status=200)

        result = self.scanner.enumerate_plugins(self.base_url)

        assert result == ["supermodule"], "Should have detected the \
                'supermodule' module."

    def test_gets_modules(self):
        # unwrap the generator
        plugins_generator = self.scanner.plugins_get()
        plugins = []
        for plugin in plugins_generator:
            plugins.append(plugin)

        l = file_len(self.scanner.plugins_file)

        assert l == len(plugins), "Should have read the contents of the file."



