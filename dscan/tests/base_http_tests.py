from cement.utils import test
from common import file_len, base_url, ProgressBar, StandardOutput
from common.testutils import decallmethods
from concurrent.futures import ThreadPoolExecutor, Future
from mock import patch, MagicMock, ANY
from plugins.drupal import Drupal
from common import ScanningMethod, Verb, Enumerate
from requests.exceptions import ConnectionError
from tests import BaseTest
import common
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
        "supermodule", "supermodule2"])
    def test_plugins_multiple_base_url(self, m):
        # mock all the urls.
        base_1 = self.base_url + "sites/all/modules/%s/"
        base_2 = self.base_url + "sites/default/modules/%s/"
        self.respond_several(base_1, {200: ["supermodule"],
            404: ["nonexistant1", "supermodule2"]})
        self.respond_several(base_2, {200:
            ["supermodule2"], 404: ["nonexistant1", "supermodule"]})

        result, empty = self.scanner.enumerate_plugins(self.base_url,
                self.scanner.plugins_base_url, ScanningMethod.ok)

        expected_1 = {'url': base_1 % 'supermodule', 'name': 'supermodule'}
        expected_2 = {'url': base_2 % 'supermodule2', 'name': 'supermodule2'}

        expected_result = [expected_1, expected_2]

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
        m = self.mock_controller('drupal', '_determine_scanning_method',
                side_effect=["forbidden"])

        self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        m.assert_called_with(self.base_url, 'head', 15)

    def test_determine_forbidden(self):
        self.add_argv(self.param_plugins)

        self.respond_several(self.base_url + "%s", {403: ["misc/"], 200:
            ["misc/drupal.js"], 404: [self.scanner.not_found_url]})

        m = self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        self.assert_called_contains(m, 'scanning_method', ScanningMethod.forbidden)

    def test_determine_not_found(self):
        self.add_argv(self.param_plugins)

        self.respond_several(self.base_url + "%s", {404: ["misc/",
            self.scanner.not_found_url], 200: ["misc/drupal.js"]})

        m = self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        self.assert_called_contains(m, 'scanning_method', ScanningMethod.not_found)

    def test_determine_ok(self):
        self.add_argv(self.param_plugins)

        self.respond_several(self.base_url + "%s", {200: ["misc/",
            "misc/drupal.js"], 404: [self.scanner.not_found_url]})

        m = self.mock_controller('drupal', 'enumerate_plugins')
        self.app.run()

        self.assert_called_contains(m, 'scanning_method', ScanningMethod.ok)

    @test.raises(RuntimeError)
    def test_determine_detect_false_ok(self):
        self.add_argv(self.param_plugins)

        self.respond_several(self.base_url + "%s", {200: ["misc/",
            "misc/drupal.js", self.scanner.not_found_url]})

        m = self.mock_controller('drupal', 'enumerate_plugins')

        self.app.run()

    def test_determine_detect_false_ok_drupal(self):
        self.add_argv(self.param_plugins)

        responses.add(responses.HEAD, self.base_url +
                self.scanner.not_found_url, body='A'*1337)
        responses.add(responses.HEAD, self.base_url +
                'misc/drupal.js', body='A'*15000)
        responses.add(responses.HEAD, self.base_url + "misc/")

        m = self.mock_controller('drupal', 'enumerate_plugins')

        # Should not exception because difference in length proves that website
        # is drupal.
        self.app.run()

    def test_determine_with_multiple_ok(self):
        self.scanner.regular_file_url = ["misc/drupal_old.js", "misc/drupal.js"]
        self.respond_several(self.base_url + "%s", {200: ["misc/",
            "misc/drupal.js"], 404: ["misc/drupal_old.js",
                self.scanner.not_found_url]})

        scanning_method = self.scanner._determine_scanning_method(self.base_url,
                'head')

        assert scanning_method == ScanningMethod.ok

    @test.raises(RuntimeError)
    def test_not_cms(self):
        self.add_argv(self.param_plugins)

        self.respond_several(self.base_url + "%s", {404:
            [self.scanner.forbidden_url, self.scanner.regular_file_url,
                self.scanner.not_found_url]})
        self.app.run()

    def test_passes_verb(self):
        self.add_argv(self.param_plugins)
        self.add_argv(["--method", "forbidden"])
        self.add_argv(['--verb', 'get'])

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

        responses.add(responses.GET, self.base_url + "misc/")
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
        self.add_argv(['--url', self.base_url, '--enumerate', 'p'])

        # Trigger redirect:
        base_url_https = 'https://www.adhwuiaihduhaknbacnckajcwnncwkakncw.com/'
        m = self.mock_controller('drupal', '_determine_scanning_method',
                side_effect=[base_url_https, 'forbidden'])

        enum = self.mock_controller('drupal', 'enumerate', side_effect=[([], True)])
        self.app.run()

        self.assert_args_contains(enum, 0, base_url_https)

    def test_redirect_is_detected(self):
        base_url_https = 'https://www.adhwuiaihduhaknbacnckajcwnncwkakncw.com/'

        self.respond_several(self.base_url + "%s", {301: ["misc/",
            "misc/drupal.js"], 404: [self.scanner.not_found_url]}, headers={'location': base_url_https})

        result = self.scanner._determine_scanning_method(self.base_url,
                Verb.head)

        assert result == base_url_https

    def test_redirect_relative_path(self):
        redirect_vals = {
            '/': self.base_url,
            '/relative': self.base_url + 'relative',
            'relative': self.base_url + 'relative',
        }

        side_effect_list = []
        for relative_url in redirect_vals:
            side_effect_list.append(relative_url)
            side_effect_list.append('forbidden')

        m = self.mock_controller('drupal', '_determine_scanning_method',
                side_effect=side_effect_list)

        self.scanner._determine_scanning_method = MagicMock(side_effect=side_effect_list)

        for i in redirect_vals:
            result = self.scanner.determine_scanning_method(self.base_url,
                    Verb.head)

            expected_result = ('forbidden', redirect_vals[i])
            assert result == expected_result

    def test_redirect_relative_does_not_crash(self):
        relative_redir = '/relative'

        self.respond_several(self.base_url + "%s", {301: ["misc/",
            "misc/drupal.js"], 404: [self.scanner.not_found_url]}, headers={'location': relative_redir})

        result = self.scanner._determine_scanning_method(self.base_url, 'head')

        assert result == relative_redir

    @test.raises(RuntimeError)
    def test_redirect_once_max(self):
        self.add_argv(['--url', self.base_url, '--enumerate', 'p'])

        # Trigger redirect twice.
        base_url_https = 'https://www.adhwuiaihduhaknbacnckajcwnncwkakncw.com/'
        m = self.mock_controller('drupal', '_determine_scanning_method',
                side_effect=[base_url_https, base_url_https])

        enum = self.mock_controller('drupal', 'enumerate', side_effect=[([], True)])
        self.app.run()

    @patch.object(common.StandardOutput, 'warn')
    def test_invalid_url_file_warns(self, warn):
        """
            Test that when using a URL file, instead of throwing a fatal
            exception, a warning is given.

            Temporarilly test that an exception is thrown.
        """
        invalid_url_file = 'tests/resources/url_file_invalid.txt'
        self.add_argv(['--url-file', invalid_url_file])

        all_mocks = self.mock_all_enumerate('drupal')
        self.mock_all_url_file(invalid_url_file)
        self.app.run()

        assert warn.call_count == 2

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
        self.add_argv(['--url-file', 'tests/resources/url_file_invalid.txt'])

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
                timeout=5)

        self.assert_called_contains_all(mock_head, 'timeout', 5)

    @patch('requests.Session.get')
    def test_respects_timeout_version(self, mock_get):
        try:
            version, is_empty = self.scanner.enumerate_version(self.base_url,
                    self.xml_file, timeout=5)
        except TypeError:
            pass

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

    @patch.object(ProgressBar, 'set')
    def test_progressbar_url_file_hidden_in_ennumerate_plugins(self, p):
        try:
            self.scanner.enumerate_plugins(self.base_url,
                    self.scanner.plugins_base_url, hide_progressbar=True,
                    max_plugins=5)
        except:
            pass

        assert p.called == False

    @patch.object(ProgressBar, 'set')
    def test_progressbar_url_file_hidden_in_ennumerate_themes(self, p):
        try:
            self.scanner.enumerate_themes(self.base_url,
                    self.scanner.plugins_base_url, hide_progressbar=True, max_plugins=5)
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
            try:
                if kwargs['hide_progressbar'] == True:
                    total_hide_progressbar += 1
            except KeyError:
                pass

        assert total_hide_progressbar == 2

    def test_progressbar_url_displays(self):
        mocks = self.mock_all_enumerate('drupal')
        self.add_argv(self.param_all)
        self.add_argv(['--method', 'forbidden'])

        self.app.run()

        total_show_progressbar = 0
        for mock in mocks:
            args, kwargs = mock.call_args
            try:
                if kwargs['hide_progressbar'] == False:
                    total_show_progressbar += 1
            except KeyError:
                pass

        assert total_show_progressbar == 2

    @patch.object(Drupal, 'plugins_get', return_value=["this_exists"])
    def test_enumerate_calls_detect_file(self, m):
        imu = [('readme.txt', '')]
        ret_val = 'ret_val'
        pbu = "sites/all/modules/%s/"
        self.respond_several(self.base_url + pbu, {403: ["this_exists"]})
        with patch.object(Drupal, '_enumerate_plugin_if', return_value=ret_val) as epif:
            result, is_empty = self.scanner.enumerate_plugins(self.base_url, "%s" + pbu, imu=imu)

            epif.assert_called_with(ANY, ANY, ANY, imu)
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

        final_found = self.scanner._enumerate_plugin_if(found, 'head', 4, imu)
        imu_final = final_found[0]['imu']

        assert len(final_found) == len(found)
        assert len(imu_final) == 1
        assert imu_final[0] == {'url': 'http://adhwuiaihduhaknbacnckajcwnncwkakncw.com/sites/all/modules/this_exists/readme.txt', 'description': 'README file.'}
