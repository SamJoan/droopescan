from cement.core import controller, foundation, backend
from cement.utils import test
from droopescan import DroopeScan
from mock import patch, MagicMock
from plugins.drupal import Drupal
from common.testutils import file_len, decallmethods
import requests
import responses

class BaseTest(test.CementTestCase):
    app_class = DroopeScan
    scanner = None

    base_url = "http://adhwuiaihduhaknbacnckajcwnncwkakncw.com/"

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

@decallmethods(responses.activate)
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

    @test.raises(RuntimeError)
    def test_errors_when_invalid_method(self):
        self.add_argv(["drupal"])
        self.add_argv(self.param_plugins + ["--method", "derpo"])
        self.app.run()

    def test_calls_plugin(self):
        self.add_argv(["drupal"])
        self.add_argv(self.param_plugins)
        self.add_argv(["--method", "forbidden"])

        m = self.mock_controller('drupal', 'enumerate_plugins')

        self.app.run()
        assert m.called, "enumerate_plugins should have been called given the arguments"

@decallmethods(responses.activate)
class BasePluginTest(BaseTest):
    """
        This class should contain tests specific to Drupal
    """

    def setUp(self):
        super(BasePluginTest, self).setUp()
        self.add_argv(["drupal"])
        self.scanner = Drupal()

    def respond_several(self, base_url, data_obj):
        if 403 in data_obj:
            for item in data_obj[403]:
                responses.add(responses.GET, base_url % item, body="forbidden",
                        status=403)

        if 404 in data_obj:
            for item in data_obj[404]:
                responses.add(responses.GET, base_url % item, body="not found",
                        status=404)

        if 200 in data_obj:
            for item in data_obj[200]:
                responses.add(responses.GET, base_url % item, body="OK",
                        status=200)

    @patch.object(Drupal, 'plugins_get', return_value=["nonexistant1",
        "nonexistant2", "supermodule"])
    def test_plugins_403(self, m):
        self.respond_several(self.base_url + "sites/all/modules/%s/", {403: ["supermodule"],
            404: ["nonexistant1", "nonexistant2"]})

        result = self.scanner.enumerate_plugins(self.base_url, Drupal.ScanningMethod.forbidden)

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

    def test_override_method(self):
        self.add_argv(self.param_plugins)
        self.add_argv(["--method", "not_found"])

        m = self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        m.assert_called_with(self.base_url, self.scanner.ScanningMethod.not_found)

    def test_add_slash_to_urls(self):
        # remove slash from url.
        self.add_argv(['--url', self.base_url[:-1], '--enumerate', 'p'])

        m = self.mock_controller('drupal', 'determine_scanning_method')
        self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        m.assert_called_with(self.base_url)

    def test_determine_forbidden(self):
        self.add_argv(self.param_plugins)

        self.respond_several(self.base_url + "%s", {403: ["misc/"], 200:
            ["misc/drupal.js"]})

        m = self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        m.assert_called_with(self.base_url,
                self.scanner.ScanningMethod.forbidden)

    def test_determine_not_found(self):
        self.add_argv(self.param_plugins)

        self.respond_several(self.base_url + "%s", {404: ["misc/"], 200:
            ["misc/drupal.js"]})

        m = self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        m.assert_called_with(self.base_url,
                self.scanner.ScanningMethod.not_found)

    def test_determine_ok(self):
        self.add_argv(self.param_plugins)

        self.respond_several(self.base_url + "%s", {200: ["misc/",
            "misc/drupal.js"]})

        m = self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        m.assert_called_with(self.base_url,
                self.scanner.ScanningMethod.ok)

    @test.raises(RuntimeError)
    def test_not_cms(self):
        self.add_argv(self.param_plugins)

        self.respond_several(self.base_url + "%s", {404: ["misc/",
            "misc/drupal.js"]})
        self.app.run()




