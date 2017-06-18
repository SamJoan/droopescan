from cement.utils import test
from concurrent.futures import ThreadPoolExecutor, Future
from dscan.common import file_len, base_url, ProgressBar, StandardOutput
from dscan.common import ScanningMethod, Verb, Enumerate
from dscan.common.testutils import decallmethods
from dscan import common
from dscan.plugins.drupal import Drupal
from dscan.plugins.internal.base_plugin_internal import BasePluginInternal
from dscan.tests import BaseTest
from mock import patch, MagicMock, ANY, mock_open
from requests.exceptions import ConnectionError
import requests
import responses

class FakeRequest():
    status_code = 200
    content = "FakeRequest."

@decallmethods(responses.activate)
class BaseHttpTests(BaseTest):
    """
        Basic, generic tests that involve HTTP requests.
    """

    def setUp(self):
        super(BaseHttpTests, self).setUp()
        self.add_argv(["scan", "drupal"])
        self._init_scanner()

    @patch.object(Drupal, 'plugins_get', return_value=["nonexistant1",
        "nonexistant2", "supermodule"])
    def test_plugins_forbidden(self, m):
        self.respond_several(self.base_url + "sites/all/modules/%s/", {403: ["supermodule"],
            404: ["nonexistant1", "nonexistant2"]})

        self.scanner.plugins_base_url = "%ssites/all/modules/%s/"
        result, empty = self.scanner.enumerate_plugins(self.base_url,
                self.scanner.plugins_base_url, ScanningMethod.forbidden)

        module_name = 'supermodule'
        expected_module_url = self.scanner.plugins_base_url % (self.base_url,
                module_name)
        expected_result = [{'url': expected_module_url, 'name': module_name}]
        assert result == expected_result, "Should have detected the \
                'supermodule' module."

    @patch.object(Drupal, 'plugins_get', return_value=["nonexistant1",
        "nonexistant2", "supermodule"])
    def test_plugins_forbidden_but_not_ok(self, m):
        self.respond_several(self.base_url + "sites/all/modules/%s/", {403: ["supermodule"],
            404: ["nonexistant1"], 200: ["nonexistant2"]})

        self.scanner.plugins_base_url = "%ssites/all/modules/%s/"
        result, empty = self.scanner.enumerate_plugins(self.base_url,
                self.scanner.plugins_base_url, ScanningMethod.forbidden)

        module_name = 'supermodule'
        expected_module_url = self.scanner.plugins_base_url % (self.base_url,
                module_name)
        expected_result = [{'url': expected_module_url, 'name': module_name}]
        assert result == expected_result, "Should have detected the \
                'supermodule' module only."

    @patch.object(Drupal, 'plugins_get', return_value=["nonexistant1",
        "nonexistant2", "supermodule"])
    def test_plugins_ok(self, m):
        self.respond_several(self.base_url + "sites/all/modules/%s/", {200: ["supermodule"],
            404: ["nonexistant1", "nonexistant2"]})

        self.scanner.plugins_base_url = "%ssites/all/modules/%s/"
        result, empty = self.scanner.enumerate_plugins(self.base_url,
                self.scanner.plugins_base_url, ScanningMethod.ok)

        module_name = 'supermodule'
        expected_module_url = self.scanner.plugins_base_url % (self.base_url,
                module_name)

        expected_result = [{'url': expected_module_url, 'name': module_name}]
        assert result == expected_result, "Should have detected the \
                'supermodule' module."

    @patch.object(Drupal, 'plugins_get', return_value=["nonexistant1",
        "nonexistant2", "supermodule"])
    def test_plugins_ok_or_forbidden(self, m):
        self.respond_several(self.base_url + "sites/all/modules/%s/", {403: ["supermodule"],
            404: ["nonexistant1", "nonexistant2"]})

        self.scanner.plugins_base_url = "%ssites/all/modules/%s/"
        result, empty = self.scanner.enumerate_plugins(self.base_url,
                self.scanner.plugins_base_url, ScanningMethod.ok)

        module_name = 'supermodule'
        expected_module_url = self.scanner.plugins_base_url % (self.base_url,
                module_name)
        expected_result = [{'url': expected_module_url, 'name': module_name}]
        assert result == expected_result, "Should have detected the \
                'supermodule' module."

    @patch.object(Drupal, 'plugins_get', return_value=["nonexistant1",
        "nonexistant2", "supermodule"])
    def test_plugins_not_found(self, m):
        module_file = self.scanner.module_common_file
        self.respond_several(self.base_url + "sites/all/modules/%s", {200:
            ["supermodule/%s" % module_file], 404: ["nonexistant1", "nonexistant2",
                'supermodule', 'nonexistant1/%s' % module_file, 'nonexistant2/%s' % module_file]})

        self.scanner.plugins_base_url = "%ssites/all/modules/%s/"
        result, empty = self.scanner.enumerate_plugins(self.base_url,
                self.scanner.plugins_base_url, ScanningMethod.not_found)

        module_name = 'supermodule'
        expected_module_url = (self.scanner.plugins_base_url % (self.base_url,
                module_name))
        expected_result = [{'url': expected_module_url, 'name': module_name}]
        assert result == expected_result, "Should have detected the \
                'supermodule' module."

    @patch.object(Drupal, 'plugins_get', return_value=["nonexistant1",
        "supermodule", "supermodule2", "amazing_mod"])
    def test_plugins_multiple_base_url(self, m):
        # mock all the urls.
        base_1 = self.base_url + "sites/all/modules/%s/"
        base_2 = self.base_url + "sites/default/modules/%s/"
        base_3 = self.base_url + "modules/%s/"
        self.respond_several(base_1, {200: ["supermodule"],
            404: ["nonexistant1", "supermodule2", "amazing_mod"]})
        self.respond_several(base_2, {200:
            ["supermodule2"], 404: ["nonexistant1", "supermodule", "amazing_mod"]})
        self.respond_several(base_3, {200:
            ["amazing_mod"], 404: ["nonexistant1", "supermodule", "supermodule2"]})

        result, empty = self.scanner.enumerate_plugins(self.base_url,
                self.scanner.plugins_base_url, ScanningMethod.ok)

        expected_1 = {'url': base_1 % 'supermodule', 'name': 'supermodule'}
        expected_2 = {'url': base_2 % 'supermodule2', 'name': 'supermodule2'}
        expected_3 = {'url': base_3 % 'amazing_mod', 'name': 'amazing_mod'}

        expected_result = [expected_1, expected_2, expected_3]

        assert result == expected_result, "Should have detected the \
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

    @patch.object(ThreadPoolExecutor, '__init__')
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

        self.assert_called_contains(m, 'scanning_method', ScanningMethod.not_found)

    def test_override_plugins_base_url(self):
        new_base_url = "%ssites/specific/modules%s"
        self.add_argv(self.param_plugins)
        self.add_argv(["--method", "forbidden"])
        self.add_argv(["--plugins-base-url", new_base_url])

        m = self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        self.assert_called_contains(m, 'scanning_method', ScanningMethod.forbidden)

    def test_add_slash_to_urls(self):
        # Remove slash from URL.
        self.add_argv(['--url', self.base_url[:-1], '--enumerate', 'p'])

        # Mock return value so as not to trigger redirects.
        m = self.mock_controller('drupal', 'determine_scanning_method',
                side_effect=["forbidden"])

        self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        self.assert_args_contains(m, 0, self.base_url)

    def test_prepends_http_to_urls(self):
        # Remove http:// from URL.
        self.add_argv(['--url', self.base_url[7:], '--enumerate', 'p'])

        m = self.mock_controller('drupal', 'determine_scanning_method',
                side_effect=["forbidden"])

        self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        self.assert_args_contains(m, 0, self.base_url)

    def test_determine_forbidden(self):
        self.add_argv(self.param_plugins)

        self.respond_several(self.base_url + "%s", {403: [Drupal.forbidden_url], 200:
            ["misc/drupal.js"], 404: [self.scanner.not_found_url]})

        m = self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        self.assert_called_contains(m, 'scanning_method', ScanningMethod.forbidden)

    def test_determine_not_found(self):
        self.add_argv(self.param_plugins)

        self.respond_several(self.base_url + "%s", {404: [Drupal.forbidden_url,
            self.scanner.not_found_url], 200: ["misc/drupal.js"]})

        m = self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        self.assert_called_contains(m, 'scanning_method', ScanningMethod.not_found)

    def test_determine_ok(self):
        self.add_argv(self.param_plugins)

        self.respond_several(self.base_url + "%s", {200: [Drupal.forbidden_url,
            "misc/drupal.js"], 404: [self.scanner.not_found_url]})

        m = self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        self.assert_called_contains(m, 'scanning_method', ScanningMethod.ok)

    @test.raises(RuntimeError)
    def test_determine_detect_false_ok(self):
        self.add_argv(self.param_plugins)

        self.respond_several(self.base_url + "%s", {200: [Drupal.forbidden_url,
            "misc/drupal.js", self.scanner.not_found_url]})

        m = self.mock_controller('drupal', 'enumerate_plugins')

        self.app.run()

    def test_determine_detect_false_ok_drupal(self):
        self.add_argv(self.param_plugins)

        responses.add(responses.HEAD, self.base_url +
                self.scanner.not_found_url, body='A'*1337)
        responses.add(responses.HEAD, self.base_url +
                'misc/drupal.js', body='A'*15000)
        responses.add(responses.HEAD, self.base_url + Drupal.forbidden_url)

        m = self.mock_controller('drupal', 'enumerate_plugins')

        # Should not exception because difference in length proves that website
        # is drupal.
        self.app.run()

    def test_detects_fake_redirect(self):
        self.add_argv(self.param_plugins)
        m = self.mock_controller('drupal', 'enumerate_plugins')
        self.respond_several(self.base_url + "%s", {301: [Drupal.forbidden_url],
            200: ["misc/drupal.js"], 404: [self.scanner.not_found_url]})

        self.app.run()

        self.assert_called_contains(m, 'scanning_method', ScanningMethod.not_found)

    def test_determine_with_multiple_ok(self):
        self.scanner.regular_file_url = ["misc/drupal_old.js", "misc/drupal.js"]
        self.respond_several(self.base_url + "%s", {200: [Drupal.forbidden_url,
            "misc/drupal.js"], 404: ["misc/drupal_old.js",
                self.scanner.not_found_url]})

        scanning_method = self.scanner.determine_scanning_method(self.base_url,
                'head')

        assert scanning_method == ScanningMethod.ok

    def test_no_determine_if_not_needed(self):
        self.add_argv(['--url', self.base_url, '-e', 'v'])

        self.mock_all_enumerate('drupal')
        dsm = self.mock_controller('drupal', 'determine_scanning_method')

        self.app.run()

        assert not dsm.called

    @test.raises(RuntimeError)
    def test_not_cms(self):
        self.add_argv(self.param_plugins)

        url_list = [self.scanner.forbidden_url, self.scanner.not_found_url]

        if isinstance(self.scanner.regular_file_url, list):
            url_list += self.scanner.regular_file_url
        else:
            url_list.append(self.scanner.regular_file_url)

        self.respond_several(self.base_url + "%s", {404: url_list})
        self.app.run()

    def test_passes_verb(self):
        self.add_argv(self.param_plugins)
        self.add_argv(["--method", "forbidden"])
        self.add_argv(['--verb', 'get'])

        responses.add(responses.GET, self.base_url, status=200)
        p = self.mock_controller('drupal', 'enumerate_plugins')

        self.app.run()

        self.assert_called_contains(p, 'verb', Verb.get)

    def test_default_verb_is_head(self):
        self.add_argv(self.param_plugins)
        self.add_argv(["--method", "forbidden"])

        p = self.mock_controller('drupal', 'enumerate_plugins')

        self.app.run()

        self.assert_called_contains(p, 'verb', Verb.head)

    @patch.object(Drupal, 'plugins_get', return_value=["supermodule"])
    def test_verb_works(self, m):
        url = self.base_url + "sites/all/modules/supermodule/"
        responses.add(responses.GET, url)

        base_url = "%ssites/all/modules/%s/"
        # will exception if not get
        self.scanner.enumerate_plugins(self.base_url,
                base_url, verb='get')

    def test_determine_respects_verb(self):
        self.add_argv(self.param_plugins)
        self.add_argv(['--verb', 'get'])

        responses.add(responses.GET, self.base_url, status=200)
        responses.add(responses.GET, self.base_url + Drupal.forbidden_url)
        responses.add(responses.GET, self.base_url + "misc/drupal.js")
        responses.add(responses.GET, self.base_url + self.scanner.not_found_url,
                status=404)

        m = self.mock_controller('drupal', 'enumerate_plugins')
        # will exception if not get
        self.app.run()

    def test_finds_interesting_urls(self):
        path = self.scanner.interesting_urls[0][0]
        description = self.scanner.interesting_urls[0][1]

        self.respond_several(self.base_url + "%s", {
            200: [self.scanner.interesting_urls[0][0]],
            404: [self.scanner.interesting_urls[1][0]],
        })

        found, empty = self.scanner.enumerate_interesting(self.base_url,
                self.scanner.interesting_urls)

        expected_result = [{'url': self.base_url + path, 'description':
                description}]

        assert not empty
        assert found == expected_result

    def test_calls_enumerate_interesting(self):
        self.add_argv(self.param_interesting)
        self.add_argv(["--method", "forbidden"])

        p = self.mock_controller('drupal', 'enumerate_interesting')
        self.app.run()

        assert p.called

    def test_interesting_respects_verb(self):
        self.add_argv(self.param_interesting)
        self.add_argv(["--method", "forbidden"])
        self.add_argv(["--verb", "get"])

        path = self.scanner.interesting_urls[0][0]
        description = self.scanner.interesting_urls[0][1]
        interesting_url = self.base_url + path

        responses.add(responses.GET, self.base_url, status=200)

        urls_200 = [x[0] for x in self.scanner.interesting_urls]
        self.respond_several(self.base_url + "%s", {200:
            urls_200}, verb=responses.GET)

        self.app.run()

    @patch.object(Drupal, 'plugins_get', return_value=['supermodule',
        'nonexistant1', 'nonexistant2', 'supermodule', 'intermitent'])
    @patch.object(common.StandardOutput, 'warn')
    def test_warns_on_500(self, warn, mock):
        r_200 = ['supermodule/']
        r_404 = ['nonexistant1/', 'nonexistant2/', 'supermodule/']
        r_500 = ['intermitent/']
        self.respond_several(self.base_url + 'sites/all/modules/%s', {200:
            r_200, 404: r_404, 500: r_500})

        self.scanner.plugins_base_url = '%ssites/all/modules/%s/'
        self.mock_controller('drupal', 'enumerate_interesting')

        result, empty = self.scanner.enumerate_plugins(self.base_url,
                self.scanner.plugins_base_url, ScanningMethod.forbidden)

        assert warn.called

    def test_redirect_changes_url(self):
        responses.reset()
        self.add_argv(['--url', self.base_url, '--enumerate', 'p'])

        # Trigger redirect:
        dr = self.mock_controller('drupal', '_determine_redirect',
                return_value=self.base_url_https)
        self.mock_controller('drupal', 'determine_scanning_method',
                return_value=ScanningMethod.not_found)

        enum = self.mock_controller('drupal', 'enumerate', side_effect=[([], True)])
        self.app.run()

        self.assert_args_contains(enum, 0, self.base_url_https)

    def test_no_redirect_flag(self):
        self.add_argv(['--url', self.base_url, '--enumerate', 'p',
            '--no-follow-redirects'])

        dr = self.mock_controller('drupal', '_determine_redirect',
                return_value=self.base_url_https)
        self.mock_controller('drupal', 'determine_scanning_method',
                return_value=ScanningMethod.not_found)

        enum = self.mock_controller('drupal', 'enumerate', side_effect=[([], True)])
        self.app.run()

        assert not dr.called

    def test_redirect_with_method(self):
        responses.reset()
        self.add_argv(['--url', self.base_url, '--method', 'not_found',
            '--enumerate', 'p'])

        # Trigger redirect:
        dr = self.mock_controller('drupal', '_determine_redirect',
                return_value=self.base_url_https)

        enum = self.mock_controller('drupal', 'enumerate', side_effect=[([], True)])
        self.app.run()

        assert dr.called
        self.assert_args_contains(enum, 0, self.base_url_https)

    def test_redirect_is_detected(self):
        responses.reset()
        self.respond_several(self.base_url + "%s", {301: [""]},
                headers={'location': self.base_url_https})

        result = self.scanner._determine_redirect(self.base_url,
                Verb.head)

        assert result == self.base_url_https

    def test_redirect_no_relative(self):
        """
        Relative redirects fuck shit up in many occasions, I've seen it.
        """
        responses.reset()
        redirect_vals = {
            '/': self.base_url,
            '/relative': self.base_url,
            'relative': self.base_url
        }

        for i in redirect_vals:
            responses.add(responses.HEAD, self.base_url,
                    status=301, adding_headers={'location': i})

            ru = self.scanner._determine_redirect(self.base_url, 'head')
            assert ru == redirect_vals[i]

            responses.reset()

        responses.reset()
        another_base = self.base_url + 'subdir/'
        responses.add(responses.HEAD, another_base, status=301,
                adding_headers={'location': 'relative'})

        ru = self.scanner._determine_redirect(another_base, 'head')

        assert ru == another_base

    def test_redirect_no_same_url(self):
        """
        If redirects take us somewhere within the same URL of base url, we
        should return the base url.
        """
        responses.reset()
        responses.add(responses.HEAD, self.base_url, status=301,
                adding_headers={'location': self.base_url + "install.php"})

        ru = self.scanner._determine_redirect(self.base_url, 'head')
        assert ru == self.base_url

    def test_url_file_calls_all(self):
        self.add_argv(['--url-file', self.valid_file])

        url_scan = self.mock_controller('drupal', 'url_scan')
        self.app.run()

        assert url_scan.call_count == 3

    def test_url_file_calls_properly(self):
        self.add_argv(['--url-file', self.valid_file, '-n', '0'])

        all_mocks = self.mock_all_enumerate('drupal')
        self.mock_all_url_file(self.valid_file)

        self.app.run()

        for mock in all_mocks:
            assert mock.call_count == 3

    def test_url_file_respects_enumerate(self):
        self.add_argv(['--url-file', self.valid_file, '-n', '0', '-e', 'v'])

        ev = self.mock_controller('drupal', 'enumerate_version')
        self.mock_all_url_file(self.valid_file)

        self.app.run()

        assert ev.call_count == 3

    def test_url_file_exceptions_are_caught(self):
        self.add_argv(['--url-file', 'dscan/tests/resources/url_file_invalid.txt'])

        self.app.run()

    @patch('requests.Session.head', return_value=FakeRequest())
    def test_respects_timeout_scanning_method(self, mock_head):
        try:
            self.scanner.determine_scanning_method(self.base_url, 'head',
                    timeout=5)
        except RuntimeError:
            pass

        self.assert_called_contains_all(mock_head, 'timeout', 5)

    @patch('requests.Session.head', return_value=FakeRequest())
    def test_respects_timeout_enumerate(self, mock_head):
        self.scanner.plugins_base_url = "%ssites/all/modules/%s/"
        result, empty = self.scanner.enumerate_plugins(self.base_url,
                self.scanner.plugins_base_url, ScanningMethod.forbidden,
                imu=[('readme', '')], timeout=5)

        self.assert_called_contains_all(mock_head, 'timeout', 5)

    @patch('requests.Session.get')
    def test_respects_timeout_version(self, mock_get):
        version, is_empty = self.scanner.enumerate_version(self.base_url,
                    timeout=5)

        self.assert_called_contains_all(mock_get, 'timeout', 5)

    @patch('requests.Session.head')
    def test_respects_timeout_interesting(self, mock_head):
        found, empty = self.scanner.enumerate_interesting(self.base_url,
                self.scanner.interesting_urls, timeout=5)

        self.assert_called_contains(mock_head, 'timeout', 5)

    def test_timeout_gets_passed(self):
        self.add_argv(self.param_all)
        self.add_argv(['--timeout', '5'])
        self.add_argv(['--method', 'forbidden'])

        all_mocks = self.mock_all_enumerate('drupal')

        self.app.run()

        for mock in all_mocks:
            self.assert_called_contains(mock, 'timeout', 5)

    @patch.object(common.StandardOutput, 'warn')
    @patch.object(Future, 'result')
    def test_thread_timeout_gets_passed(self, result, warn):
        self.add_argv(self.param_plugins)
        self.add_argv(['--timeout-host', '150', '--url-file', self.valid_file, '--method', 'forbidden'])
        all_mocks = self.mock_all_enumerate('drupal')

        self.app.run()

        result.assert_called_with(timeout=150)

    def test_progressbar_url_file_hidden_in_enumerate_plugins(self):
        with patch("dscan.plugins.internal.base_plugin_internal.ProgressBar") as p:
            try:
                self.scanner.enumerate_plugins(self.base_url,
                        self.scanner.plugins_base_url, hide_progressbar=True)
            except:
                pass

            assert p.called == False

    @patch.object(ProgressBar, 'set')
    def test_progressbar_url_file_hidden_in_enumerate_themes(self, p):
        with patch("dscan.plugins.internal.base_plugin_internal.ProgressBar") as p:
            try:
                self.scanner.enumerate_themes(self.base_url,
                        self.scanner.plugins_base_url, hide_progressbar=True)
            except:
                pass

            assert p.called == False

    def test_progressbar_url_file_hidden_in_enumerate_interesting(self):
        with patch("dscan.plugins.internal.base_plugin_internal.ProgressBar") as p:
            try:
                self.scanner.enumerate_interesting(self.base_url,
                        self.scanner.plugins_base_url, hide_progressbar=True)
            except:
                pass

            assert p.called == False

    def test_progressbar_url_file_hidden_in_enumerate_version(self):
        with patch("dscan.plugins.internal.base_plugin_internal.ProgressBar") as p:
            try:
                self.scanner.enumerate_version(self.base_url,
                        self.scanner.versions_file, hide_progressbar=True)
            except:
                pass

            assert p.called == False

    def test_progressbar_url_file_hidden(self):
        mocks = self.mock_all_enumerate('drupal')
        self.add_argv(['--url-file', self.valid_file])
        self.add_argv(['--method', 'forbidden'])

        self.app.run()

        total_hide_progressbar = 0
        for mock in mocks:
            args, kwargs = mock.call_args
            if kwargs['hide_progressbar'] == True:
                total_hide_progressbar += 1

        assert total_hide_progressbar == 4

    def test_progressbar_url_displays(self):
        mocks = self.mock_all_enumerate('drupal')
        self.add_argv(self.param_all)
        self.add_argv(['--method', 'forbidden'])

        self.app.run()

        total_show_progressbar = 0
        for mock in mocks:
            args, kwargs = mock.call_args
            if kwargs['hide_progressbar'] == False:
                total_show_progressbar += 1

        assert total_show_progressbar == 4

    @patch.object(Drupal, 'plugins_get', return_value=["this_exists"])
    def test_enumerate_calls_detect_file(self, m):
        imu = [('readme.txt', '')]
        ret_val = 'ret_val'
        pbu = "sites/all/modules/%s/"
        self.respond_several(self.base_url + pbu, {403: ["this_exists"]})
        with patch.object(Drupal, '_enumerate_plugin_if', return_value=ret_val) as epif:
            result, is_empty = self.scanner.enumerate_plugins(self.base_url, "%s" + pbu, imu=imu)

            args, kwargs = epif.call_args
            assert args[3] == imu
            assert result == ret_val
            assert is_empty == False

    @patch.object(Drupal, 'plugins_get', return_value=["this_exists"])
    def test_doesnt_call_detect_file_if_no_variable(self, m):
        pbu = "sites/all/modules/%s/"
        self.respond_several(self.base_url + pbu, {403: ["this_exists"]})
        with patch.object(Drupal, '_enumerate_plugin_if') as epif:
            result, is_empty = self.scanner.enumerate_plugins(self.base_url, "%s" + pbu)

            assert not epif.called

    @patch.object(Drupal, 'plugins_get', return_value=["this_exists"])
    def test_detect_imu(self, m):
        readme_imu = ('readme.txt', 'README file.')
        http_responses_map = {403: ["this_exists/"], 200: ["this_exists/readme.txt"], 404: ["this_exists/LICENSE.txt", "this_exists/API.txt"]}
        imu = [readme_imu, ('LICENSE.txt', 'License file.'), ('API.txt', 'Contains API documentation for the module.')]
        found = [{'name': 'this_exists', 'url': 'http://adhwuiaihduhaknbacnckajcwnncwkakncw.com/sites/all/modules/this_exists/'}]

        pbu = "sites/all/modules/%s"
        self.respond_several(self.base_url + pbu, http_responses_map)

        final_found = self.scanner._enumerate_plugin_if(found, 'head', 4, imu,
                True, 15, {})
        imu_final = final_found[0]['imu']

        assert len(final_found) == len(found)
        assert len(imu_final) == 1
        assert imu_final[0] == {'url': 'http://adhwuiaihduhaknbacnckajcwnncwkakncw.com/sites/all/modules/this_exists/readme.txt', 'description': 'README file.'}

    def test_less_themes_by_default(self):
        self.add_argv(['--method', 'forbidden', '-u', self.base_url])

        all_mocks = self.mock_all_enumerate('drupal')

        self.app.run()

        themes_ok = False
        plugins_ok = False
        for m in all_mocks:
            args, kwargs = m.call_args
            if 'max_plugins' in kwargs:
                mp = kwargs['max_plugins']
                if mp == BasePluginInternal.NUMBER_THEMES_DEFAULT:
                    themes_ok = True

                if mp == BasePluginInternal.NUMBER_PLUGINS_DEFAULT:
                    plugins_ok = True


        assert themes_ok
        assert plugins_ok

    def test_url_file_ip_url_list(self):
        self.add_argv(['--url-file', self.valid_file_ip])
        with patch('requests.Session.head', autospec=True) as h:
            with patch('dscan.plugins.internal.base_plugin_internal.BasePluginInternal.determine_scanning_method', side_effect=RuntimeError):
                h.return_value.status_code = 200
                self.app.run()

                calls = h.call_args_list

                args, kwargs = calls[0]
                assert args[1] == 'http://192.168.1.1/'
                assert kwargs['headers']['Host'] == 'example.com'

                args, kwargs = calls[1]
                assert args[1] == 'http://192.168.1.1/'
                assert kwargs['headers']['Host'] == 'example.com'

                args, kwargs = calls[2]
                assert args[1] == 'http://192.168.1.2/drupal/'
                assert kwargs['headers']['Host'] == 'example.com'

    @patch('requests.Session.head', return_value=FakeRequest())
    def test_respects_host_redirect(self, mock_head):
        try:
            self.scanner._determine_redirect(self.base_url, 'head',
                    headers=self.host_header)
        except RuntimeError:
            pass

        self.assert_called_contains_all(mock_head, 'headers', self.host_header)

    @patch('requests.Session.head', return_value=FakeRequest())
    def test_respects_host_scanning_method(self, mock_head):
        try:
            self.scanner.determine_scanning_method(self.base_url, 'head',
                    headers=self.host_header)
        except RuntimeError:
            pass

        self.assert_called_contains_all(mock_head, 'headers', self.host_header)

    @patch('requests.Session.head', return_value=FakeRequest())
    def test_respects_host_enumerate(self, mock_head):
        self.scanner.plugins_base_url = "%ssites/all/modules/%s/"
        result, empty = self.scanner.enumerate_plugins(self.base_url,
                self.scanner.plugins_base_url, ScanningMethod.forbidden,
                imu=[('readme', '')], headers=self.host_header)

        self.assert_called_contains_all(mock_head, 'headers', self.host_header)

    @patch('requests.Session.get')
    def test_respects_host_version(self, mock_get):
        version, is_empty = self.scanner.enumerate_version(self.base_url,
                headers=self.host_header)

        self.assert_called_contains_all(mock_get, 'headers', self.host_header)

    @patch('requests.Session.head')
    def test_respects_host_interesting(self, mock_head):
        found, empty = self.scanner.enumerate_interesting(self.base_url,
                self.scanner.interesting_urls, headers=self.host_header)

        self.assert_called_contains(mock_head, 'headers', self.host_header)

    def test_host_gets_passed(self):
        self.add_argv(self.param_all)
        self.add_argv(['--host', 'example.com'])
        self.add_argv(['--method', 'forbidden'])

        all_mocks = self.mock_all_enumerate('drupal')

        self.app.run()

        for mock in all_mocks:
            self.assert_called_contains(mock, 'headers', self.host_header)

    def test_determine_scanning_method_edge_case(self):
        self.add_argv(['-U', self.valid_file, '-e', 'v',
            '--no-follow-redirects'])

        ev = self.mock_controller('drupal', 'enumerate_version')
        ev.side_effect = [(None, True), (None, True), (['7.0'], False)]

        dsm = self.mock_controller('drupal', 'determine_scanning_method')
        dsm.return_value = ScanningMethod.forbidden

        with patch('dscan.common.output.StandardOutput.print') as p:
            self.app.run()

            assert p.call_count == 1

    def test_redirect_is_output(self):
        all_mocks = self.mock_all_enumerate('drupal')

        self.add_argv(['-u', self.base_url, '--method', 'forbidden'])

        dr = self.mock_controller('drupal', '_determine_redirect')
        dr.return_value = self.base_url_https
        with patch('dscan.common.output.StandardOutput.echo') as e:
            self.app.run()

            args, kwargs = e.call_args_list[0]
            outputs_redirect_url = self.base_url_https in args[0]
            assert outputs_redirect_url

        assert dr.called
