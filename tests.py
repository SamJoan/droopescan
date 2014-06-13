from cement.core import controller, foundation, backend
from cement.utils import test
from common.testutils import file_len, decallmethods
from droopescan import DroopeScan
from mock import patch, MagicMock
from plugins.drupal import Drupal
from requests.exceptions import ConnectionError
from requests_futures.sessions import FuturesSession
import requests
import responses

class BaseTest(test.CementTestCase):
    app_class = DroopeScan
    scanner = None

    base_url = "http://adhwuiaihduhaknbacnckajcwnncwkakncw.com/"

    param_base = ["--url", base_url, '-n', '10']
    param_plugins = param_base + ["-e", 'p']
    param_themes = param_base + ["-e", 't']
    param_all = param_base + ["-e", 'a']

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

    def mock_controller(self, plugin_label, method, return_value = None, side_effect = None):
        """
            Mocks controller by label. Can only be used to test controllers
            that get instantiated automatically by cement.
        """
        m = MagicMock()
        if return_value:
            m.return_value = return_value

        if side_effect:
            m.side_effect = side_effect

        setattr(backend.__handlers__['controller'][plugin_label], method, m)
        return m

    def add_argv(self, argv):
        """
        Concatenates list with self.app.argv.
        """
        self.app._meta.argv += argv

    def assert_called_contains(self, mocked_method, position, thing):
        """
            asserts that the parameter in position 'position' equals 'thing' in
            the first call to mocked_method.
            @param mocked_method
            @param position the position the argument is. It starts at 0 and
            discounts self. e.g. (self, a, b, c): position of b -> 1
        """

        first_call = mocked_method.call_args_list[0][0]
        assert first_call[position] == thing, "Parameter is not as expected."


@decallmethods(responses.activate)
class BasePluginTest(BaseTest):

    def setUp(self):
        super(BasePluginTest, self).setUp()
        self.add_argv(["drupal"])
        self.scanner = Drupal()

    def respond_several(self, base_url, data_obj):
        for status_code in data_obj:
            for item in data_obj[status_code]:
                url = base_url % item
                responses.add(responses.GET, url,
                        body=str(status_code), status=status_code)

    @patch.object(Drupal, 'plugins_get', return_value=["nonexistant1",
        "nonexistant2", "supermodule"])
    def test_plugins_forbidden(self, m):
        self.respond_several(self.base_url + "sites/all/modules/%s/", {403: ["supermodule"],
            404: ["nonexistant1", "nonexistant2"]})

        self.scanner.plugins_base_url = "%ssites/all/modules/%s/"
        result = self.scanner.enumerate_plugins(self.base_url,
                self.scanner.plugins_base_url, Drupal.ScanningMethod.forbidden)

        assert result == ["supermodule"], "Should have detected the \
                'supermodule' module."

    @patch.object(Drupal, 'plugins_get', return_value=["nonexistant1",
        "nonexistant2", "supermodule"])
    def test_plugins_ok(self, m):
        self.respond_several(self.base_url + "sites/all/modules/%s/", {200: ["supermodule"],
            404: ["nonexistant1", "nonexistant2"]})

        self.scanner.plugins_base_url = "%ssites/all/modules/%s/"
        result = self.scanner.enumerate_plugins(self.base_url,
                self.scanner.plugins_base_url, Drupal.ScanningMethod.ok)

        assert result == ["supermodule"], "Should have detected the \
                'supermodule' module."

    @patch.object(Drupal, 'plugins_get', return_value=["nonexistant1",
        "nonexistant2", "supermodule"])
    def test_plugins_not_found(self, m):
        self.respond_several(self.base_url + "sites/all/modules/%s", {200:
            ["supermodule/README.txt"], 404: ["nonexistant1", "nonexistant2",
                'supermodule', 'nonexistant1/README.txt', 'nonexistant2/README.txt']})

        self.scanner.plugins_base_url = "%ssites/all/modules/%s/"
        result = self.scanner.enumerate_plugins(self.base_url,
                self.scanner.plugins_base_url, Drupal.ScanningMethod.not_found)

        assert result == ["supermodule"], "Should have detected the \
                'supermodule' module."

    @patch.object(Drupal, 'plugins_get', return_value=["nonexistant1",
        "supermodule", "supermodule2"])
    def test_plugins_multiple_base_url(self, m):

        # mock all the urls.
        self.respond_several(self.base_url + "sites/all/modules/%s/", {200: ["supermodule"],
            404: ["nonexistant1", "supermodule2"]})
        self.respond_several(self.base_url + "sites/default/modules/%s/", {200:
            ["supermodule2"], 404: ["nonexistant1", "supermodule"]})

        result = self.scanner.enumerate_plugins(self.base_url,
                self.scanner.plugins_base_url, Drupal.ScanningMethod.ok)

        assert result == ["supermodule", "supermodule2"], "Should have detected the \
                'supermodule' module."

    def test_gets_modules(self):
        # unwrap the generator
        plugins_generator = self.scanner.plugins_get()
        plugins = []
        for plugin in plugins_generator:
            plugins.append(plugin)

        l = file_len(self.scanner.plugins_file)

        assert l == len(plugins), "Should have read the contents of the file."

    def test_limits_by_number(self):
        plugins_generator = self.scanner.plugins_get("3")

        plugins = []
        for plugin in plugins_generator:
            plugins.append(plugin)

        assert 3 == len(plugins)

        themes_generator = self.scanner.themes_get("3")

        themes = []
        for theme in themes_generator:
            themes.append(theme)

        assert 3 == len(themes)

    @patch.object(FuturesSession, '__init__')
    def test_threads_gets_passed(self, ffs):
        self.add_argv(self.param_plugins)
        self.add_argv(['--threads', '30', '--method', 'forbidden'])
        try:
            self.app.run()
        except:
            # this will never happen. j/k this will always happen.
            pass

        ffs.assert_called_with(max_workers=30)

    def test_number_param_passed_plugins(self):
        self.add_argv(self.param_plugins)
        self.add_argv(['--number', '30', '--method', 'forbidden'])

        m = self.mock_controller('drupal', 'plugins_get')
        self.app.run()

        m.assert_called_with('30')

    def test_number_param_passed_themes(self):
        self.add_argv(self.param_themes)
        self.add_argv(['--number', '30', '--method', 'forbidden'])

        m = self.mock_controller('drupal', 'themes_get')
        self.app.run()

        m.assert_called_with('30')

    def test_override_method(self):
        self.add_argv(self.param_plugins)
        self.add_argv(["--method", "not_found"])

        m = self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        self.assert_called_contains(m, 2, self.scanner.ScanningMethod.not_found)

    def test_override_plugins_base_url(self):
        new_base_url = "%ssites/specific/modules%s"
        self.add_argv(self.param_plugins)
        self.add_argv(["--method", "forbidden"])
        self.add_argv(["--plugins-base-url", new_base_url])

        m = self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        self.assert_called_contains(m, 2, self.scanner.ScanningMethod.forbidden)

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

        self.assert_called_contains(m, 2, self.scanner.ScanningMethod.forbidden)

    def test_determine_not_found(self):
        self.add_argv(self.param_plugins)

        self.respond_several(self.base_url + "%s", {404: ["misc/"], 200:
            ["misc/drupal.js"]})

        m = self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        self.assert_called_contains(m, 2, self.scanner.ScanningMethod.not_found)

    def test_determine_ok(self):
        self.add_argv(self.param_plugins)

        self.respond_several(self.base_url + "%s", {200: ["misc/",
            "misc/drupal.js"]})

        m = self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        self.assert_called_contains(m, 2, self.scanner.ScanningMethod.ok)

    def test_determine_with_multiple_ok(self):
        self.scanner.regular_file_url = ["misc/drupal_old.js", "misc/drupal.js"]
        self.respond_several(self.base_url + "%s", {200: ["misc/",
            "misc/drupal.js"], 404: ["misc/drupal_old.js"]})

        scanning_method = self.scanner.determine_scanning_method(self.base_url)

        assert scanning_method == self.scanner.ScanningMethod.ok

    @test.raises(RuntimeError)
    def test_not_cms(self):
        self.add_argv(self.param_plugins)

        self.respond_several(self.base_url + "%s", {404: ["misc/",
            "misc/drupal.js"]})
        self.app.run()

@decallmethods(responses.activate)
class DrupalScanTest(BaseTest):
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
    def test_errors_when_invalid_enumerate(self):
        self.add_argv(["drupal"])
        self.add_argv(self.param_base + ["-e", 'z'])
        self.app.run()

    @test.raises(RuntimeError)
    def test_errors_when_invalid_method(self):
        self.add_argv(["drupal"])
        self.add_argv(self.param_plugins + ["--method", "derpo"])
        self.app.run()

    @test.raises(ConnectionError)
    def test_calls_plugin(self):
        self.add_argv(["drupal"])
        self.add_argv(self.param_plugins)
        self.add_argv(["--method", "forbidden"])

        self.app.run()

    @test.raises(ConnectionError)
    def test_calls_theme(self):
        self.add_argv(["drupal"])
        self.add_argv(self.param_themes)

        self.add_argv(["--method", "forbidden"])

        self.app.run()

    def test_calls_all(self):
        self.add_argv(["drupal"])
        self.add_argv(self.param_all)
        self.add_argv(["--method", "forbidden"])

        p = self.mock_controller("drupal", 'enumerate_plugins')
        t = self.mock_controller("drupal", 'enumerate_themes')
        u = self.mock_controller("drupal", 'enumerate_users')

        self.app.run()

        assert p.called
        assert t.called
        assert u.called

    def test_doesnt_crash_on_runtimeerror(self):
        self.add_argv(["drupal"])
        self.add_argv(self.param_all)
        self.add_argv(["--method", "forbidden"])

        p = self.mock_controller("drupal", 'enumerate_plugins')
        t = self.mock_controller("drupal", 'enumerate_themes')
        u = self.mock_controller("drupal", 'enumerate_users', side_effect=RuntimeError("derp!"))

        self.app.run()



