from cement.core import controller, foundation, backend, handler
from cement.utils import test
from cement.utils.misc import init_defaults
from dscan.common.testutils import decallmethods
from dscan.droopescan import DroopeScan, reorder_argv_for_backward_compatibility
from dscan.plugins.drupal import Drupal
from dscan.plugins import Scan
from lxml import etree
from mock import patch, MagicMock
from nose.tools import raises
import os
import responses
import dscan
import unittest

# Provide test.raises for backward compatibility with existing test code
test.raises = raises

BASE_URL = "http://adhwuiaihduhaknbacnckajcwnncwkakncw.com/"
BASE_URL_HTTPS = "https://adhwuiaihduhaknbacnckajcwnncwkakncw.com/"
VALID_FILE = 'dscan/tests/resources/url_file_valid.txt'
VALID_FILE_IP = 'dscan/tests/resources/url_file_ip_url.txt'
EMPTY_FILE = 'dscan/tests/resources/empty_file'

class MockHash():
    files = None
    def mock_func(self, *args, **kwargs):
        url = kwargs['file_url']
        try:
            return self.files[url]
        except KeyError:
            raise RuntimeError(url)

class TestDroopeScan(DroopeScan):
    def run(self):
        self._meta.argv = reorder_argv_for_backward_compatibility(list(self._meta.argv))
        super(TestDroopeScan, self).run()

class BaseTest(unittest.TestCase):
    app_class = TestDroopeScan
    scanner = None

    base_url = BASE_URL
    base_url_https = BASE_URL_HTTPS
    valid_file = VALID_FILE
    valid_file_ip = VALID_FILE_IP
    empty_file = EMPTY_FILE

    param_base = ["--url", base_url, '-n', '10']
    param_plugins = param_base + ["-e", 'p']
    param_interesting = param_base + ["-e", 'i']
    param_themes = param_base + ["-e", 't']
    param_version = param_base + ["-e", 'v']
    param_all = param_base + ["-e", 'a']

    versions_xsd = 'dscan/common/versions.xsd'
    xml_file = 'dscan/tests/resources/versions.xml'

    test_opts = {
        'output': 'standard',
        'debug_requests': False,
        'error_log': '-',
        'threads': 1,
        'threads_enumerate': None,
        'threads_identify': None,
        'threads_scan': None,
        'verb': 'head',
        'timeout': 300,
        'plugins_base_url': None,
        'themes_base_url': None,
        'number': 10,
        'debug': False,
        'enumerate': 'a',
        'headers': {},
        'cookie': None,
        'hide_progressbar': False,
        'no_fingerprint_fallback': False,
        'user_agent': 'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0'
    }

    host_header = {'Host': 'example.com'}

    def setUp(self):
        super(BaseTest, self).setUp()

        defaults = init_defaults('DroopeScan', 'general')
        defaults['general']['pwd'] = os.getcwd()
        # Cement 3: plugin directories are now configured in Meta class
        self.app = TestDroopeScan(argv=[], config_defaults=defaults, catch_signals=None)

        # Cement 3: register handlers via app instance
        self.app.handler.register(Scan)
        self.app.testing = True
        self.app.setup()
        responses.add(responses.HEAD, self.base_url, status=200)

    def _init_scanner(self):
        self.scanner = Drupal()
        self.scanner._general_init(self.test_opts)
        self.scanner._determine_fake_200_module = self._fake_200_check
        m = self.mock_controller('drupal', '_determine_fake_200_module',
                return_value=False)

    def _fake_200_check(self, param1, param2, param3):
        return False

    def tearDown(self):
        self.app.close()

    def mock_controller(self, plugin_label, method, return_value = None,
            side_effect = None, mock = None):
        """
        Mocks controller by label. Can only be used to test controllers
        that get instantiated automatically by cement.
        @param plugin_label: e.g. 'drupal'
        @param method: e.g. 'enumerate_plugins'
        @param return_value: what to return. Default is None, unless the
            method starts with enumerate_*, in which case the result is a
            tuple as expected by BasePlugin.
        @param mock: the MagicMock to place. If None, a blank MagicMock is
            created.
        @param side_effect: if set to an exception, it will raise an
            exception.
        """
        if mock:
            m = mock
        else:
            m = MagicMock()

        if return_value != None:
            m.return_value = return_value
        else:
            if method.startswith("enumerate_"):
                m.return_value = ({"a":[]}, True)

        if side_effect:
            m.side_effect = side_effect

        setattr(self.controller_get(plugin_label), method, m)
        return m

    def controller_get(self, plugin_label):
        # Cement 3: use app.handler to get controllers
        return self.app.handler.get('controller', plugin_label)

    def add_argv(self, argv):
        """
            Concatenates list with self.app.argv.
        """
        self.app._meta.argv += argv

    def clear_argv(self):
        self.app._meta.argv = []

    def assert_called_contains(self, mocked_method, kwarg_name, kwarg_value):
        """
        Assert kwarg_name: equals kwarg name in call to mocked_method.
        @param mocked_method: mock to check the call to.
        @param kwarg_name: name of the param. E.g. 'url'
        @param kwarg_value: expected value. E.g. 'https://www.drupal.org/'
        """
        args, kwargs = mocked_method.call_args
        actual_value = kwargs[kwarg_name]
        if isinstance(kwarg_value, dict) and isinstance(actual_value, dict):
            assert all(item in actual_value.items() for item in kwarg_value.items()), "Parameter is not as expected (subset check)."
        else:
            assert actual_value == kwarg_value, "Parameter is not as expected."

    def assert_called_contains_all(self, mocked_method, kwarg_name, kwarg_value):
        call_list = mocked_method.call_args_list
        if len(mocked_method.call_args_list) == 0:
            assert False, "No calls to mocked method"

        for args, kwargs in call_list:
            actual_value = kwargs[kwarg_name]
            if isinstance(kwarg_value, dict) and isinstance(actual_value, dict):
                assert all(item in actual_value.items() for item in kwarg_value.items()), "Parameter is not as expected (subset check)."
            else:
                assert actual_value == kwarg_value, "Parameter is not as expected."

    def assert_args_contains(self, mocked_method, position, expected_value):
        """
        Assert that the call contains this argument in the args at position position.
        """
        args, kwargs = mocked_method.call_args
        assert args[position] == expected_value

    def respond_several(self, base_url, data_obj, verb=responses.HEAD, headers=[]):
        for status_code in data_obj:
            for item in data_obj[status_code]:
                url = base_url % item
                body_content = str(status_code)
                req_headers = headers.copy() if isinstance(headers, dict) else {}
                if verb == responses.HEAD:
                    req_headers['Content-Length'] = str(len(body_content))
                    responses.add(verb, url,
                            body="", status=status_code,
                            adding_headers=req_headers)
                else:
                    responses.add(verb, url,
                            body=body_content, status=status_code,
                            adding_headers=headers)

    def mock_all_enumerate(self, plugin_name):
        all = []
        all.append(self.mock_controller(plugin_name, 'enumerate_plugins'))
        all.append(self.mock_controller(plugin_name, 'enumerate_themes'))
        all.append(self.mock_controller(plugin_name, 'enumerate_interesting'))

        for a in all:
            all[a].return_value = ([], True)

        mock_version = self.mock_controller(plugin_name, 'enumerate_version')
        mock_version.return_value = (['7.32'], False)
        all.append(mock_version)

        return all

    def mock_all_url_file(self, url_file):
        with open(url_file) as f:
            for url in f:
                url_tpl = url.strip('\n') + '%s'

                self.respond_several(url_tpl, {
                    403: [Drupal.forbidden_url],
                    200: ['', 'misc/drupal.js'],
                    404: [
                        self.scanner.not_found_url,
                        '/sites/all/modules/a12abb4d5bead1220174a6b39a2546db/',

                    ]
                })

    def mock_xml(self, xml_file, version_to_mock):
        '''
        Generates all mock data, and returns a MagicMock which can be used
        to replace self.scanner.enumerate_file_hash.

        self.scanner.enumerate_file_hash = self.mock_xml(self.xml_file, "7.27")

        @param xml_file: a file, which contains the XML to mock.
        @param version_to_mock: the version which we will pretend to be.
        @return: a function which can be used to mock
            BasePlugin.enumerate_file_hash
        '''
        with open(xml_file) as f:
            doc = etree.fromstring(f.read())
            files_xml = doc.xpath('//cms/files/file')

            files = {}
            for file in files_xml:
                url = file.get('url')
                versions = file.xpath('version')
                for file_version in versions:
                    version_number = file_version.get('nb')
                    md5 = file_version.get('md5')

                    if version_number == version_to_mock:
                        files[url] = md5

                if not url in files:
                    files[url] = '5d41402abc4b2a76b9719d911017c592'

            ch_xml_all = doc.findall('./files/changelog')
            if len(ch_xml_all) > 0:
                for ch_xml in ch_xml_all:
                    ch_url = ch_xml.get('url')
                    ch_versions = ch_xml.findall('./version')
                    found = False
                    for ch_version in ch_versions:
                        ch_nb = ch_version.get('nb')
                        if ch_nb == version_to_mock:
                            files[ch_url] = ch_version.get('md5')
                            found = True

        mock_hash = MockHash()
        mock_hash.files = files
        mock = MagicMock(side_effect=mock_hash.mock_func)

        return mock

    def get_dispatched_controller(self, app):
        """
        This might be considered a hack. I should eventually get in touch
        with the cement devs and ask for a better alternative :P.
        """
        return app.controller._dispatch_command['controller']\
                ._dispatch_command['controller']

