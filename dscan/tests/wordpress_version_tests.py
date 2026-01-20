from dscan.tests import BaseTest
from dscan.plugins.wordpress import Wordpress
import responses
from mock import patch, MagicMock

class WordpressVersionTests(BaseTest):
    def setUp(self):
        super(WordpressVersionTests, self).setUp()
        self.add_argv(['scan', 'wordpress'])
        self.add_argv(['--method', 'forbidden'])
        self._init_scanner()
        # Mock the VersionsFile to avoid file system issues and speed up tests
        self.scanner.vf = MagicMock()
        self.scanner.vf.files_get.return_value = []
        self.scanner.vf.version_get.return_value = []

    def _init_scanner(self):
        self.scanner = Wordpress()
        self.scanner._general_init(self.test_opts)

    @responses.activate
    def test_version_from_html_meta_tag(self):
        url = self.base_url
        body = '<html><head><meta name="generator" content="WordPress 6.9" /></head><body></body></html>'
        responses.add(responses.GET, url, body=body, status=200)

        version = self.scanner.enumerate_version_from_html(url)
        assert version == "6.9"

    @responses.activate
    def test_version_from_html_meta_tag_case_insensitive(self):
        url = self.base_url
        body = '<html><head><META NAME="GENERATOR" CONTENT="WordPress 6.9" /></head><body></body></html>'
        responses.add(responses.GET, url, body=body, status=200)

        version = self.scanner.enumerate_version_from_html(url)
        assert version == "6.9"

    @responses.activate
    def test_version_from_html_not_found(self):
        url = self.base_url
        body = '<html><head></head><body></body></html>'
        responses.add(responses.GET, url, body=body, status=200)

        version = self.scanner.enumerate_version_from_html(url)
        assert version is None

    @responses.activate
    def test_enumerate_version_integration(self):
        url = self.base_url
        body = '<html><head><meta name="generator" content="WordPress 6.9" /></head><body></body></html>'
        responses.add(responses.GET, url, body=body, status=200)
        
        # Mock parent enumerate_version to return empty list
        with patch('dscan.plugins.internal.base_plugin.BasePlugin.enumerate_version', return_value=([], True)):
            versions, is_empty = self.scanner.enumerate_version(url)
            assert versions == ["6.9"]
            assert is_empty == False

    @responses.activate
    def test_enumerate_version_conflict_prioritizes_fingerprint(self):
        url = self.base_url
        body = '<html><head><meta name="generator" content="WordPress 6.9" /></head><body></body></html>'
        responses.add(responses.GET, url, body=body, status=200)
        
        # Mock parent enumerate_version to return a different version
        with patch('dscan.plugins.internal.base_plugin.BasePlugin.enumerate_version', return_value=(["5.0"], False)):
            versions, is_empty = self.scanner.enumerate_version(url)
            # According to my implementation, if conflict, it returns fingerprint versions
            assert versions == ["5.0"]
            assert is_empty == False

    @responses.activate
    def test_enumerate_version_consistent(self):
        url = self.base_url
        body = '<html><head><meta name="generator" content="WordPress 6.9" /></head><body></body></html>'
        responses.add(responses.GET, url, body=body, status=200)
        
        # Mock parent enumerate_version to return the same version
        with patch('dscan.plugins.internal.base_plugin.BasePlugin.enumerate_version', return_value=(["6.9", "6.9.1"], False)):
            versions, is_empty = self.scanner.enumerate_version(url)
            assert versions == ["6.9"]
            assert is_empty == False
