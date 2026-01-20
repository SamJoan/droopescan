from cement.utils import test
from dscan.common.testutils import decallmethods, xml_validate
from dscan.common import VersionsFile
from glob import glob
from lxml import etree
from mock import patch, MagicMock
from dscan.plugins.drupal import Drupal
from dscan.plugins.internal.scan import Scan
from requests.exceptions import ConnectionError
from dscan.tests import BaseTest
import dscan
import hashlib
import requests
import responses

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

@decallmethods(responses.activate)
class FingerprintTests(BaseTest):
    '''
        Tests related to version fingerprinting for all plugins.
    '''

    bpi_module = 'dscan.plugins.internal.base_plugin_internal.BasePluginInternal.'
    xml_file_changelog = 'dscan/tests/resources/versions_with_changelog.xml'
    cms_identify_module = bpi_module + 'cms_identify'
    process_url_module = bpi_module + 'process_url'
    pui_module = bpi_module + 'process_url_iterable'
    efh_module = bpi_module + 'enumerate_file_hash'
    redir_module = bpi_module + '_determine_redirect'
    warn_module = 'dscan.common.output.StandardOutput.warn'

    p_list = []

    def setUp(self):
        super(FingerprintTests, self).setUp()
        self.add_argv(['scan', 'drupal'])
        self.add_argv(['--method', 'forbidden'])
        self.add_argv(self.param_version)
        self._init_scanner()
        self.v = VersionsFile(self.xml_file)

    def tearDown(self):
        self._mock_cms_multiple_stop()

    @patch('dscan.common.VersionsFile.files_get', return_value=['misc/drupal.js'])
    @patch('dscan.common.VersionsFile.changelogs_get', return_value=['CHANGELOG.txt'])
    def test_calls_version(self, m, n):
        responses.add(responses.GET, self.base_url + 'misc/drupal.js')
        responses.add(responses.GET, self.base_url + 'CHANGELOG.txt')
        # with no mocked calls, any HTTP req will cause a ConnectionError.
        self.app.run()

    @test.raises(ConnectionError)
    def test_calls_version_no_mock(self):
        # with no mocked calls, any HTTP req will cause a ConnectionError.
        self.app.run()

    def test_xml_validates_all(self):
        for xml_path in glob(dscan.PWD + 'plugins/*/versions.xml'):
            print(xml_path)
            try: 
                xml_validate(xml_path, self.versions_xsd)
            except etree.XMLSyntaxError as err:
                raise Exception("XML Validation failed for %s: %s" % (xml_path, str(err)))

    def test_determines_version(self):
        real_version = '7.26'
        self.scanner.enumerate_file_hash = self.mock_xml(self.xml_file, real_version)

        self.scanner.vf = VersionsFile(self.xml_file)
        version, is_empty = self.scanner.enumerate_version(self.base_url)

        assert version[0] == real_version
        assert is_empty == False

    def test_determines_version_similar(self):
        real_version = '6.15'
        self.scanner.enumerate_file_hash = self.mock_xml(self.xml_file, real_version)
        self.scanner.vf = VersionsFile(self.xml_file)
        returned_version, is_empty = self.scanner.enumerate_version(self.base_url)

        assert len(returned_version) == 2
        assert real_version in returned_version
        assert is_empty == False

    def test_enumerate_hash(self):
        file_url = '/misc/drupal.js'
        body = 'zjyzjy2076'
        responses.add(responses.GET, self.base_url + file_url, body=body)

        actual_md5 = hashlib.md5(body.encode('utf-8')).hexdigest()

        md5 = self.scanner.enumerate_file_hash(self.base_url, file_url)

        assert md5 == actual_md5

    @test.raises(RuntimeError)
    def test_enumerate_not_found(self):
        ch_url = "CHANGELOG.txt"
        responses.add(responses.GET, self.base_url + ch_url, status=404)

        self.scanner.enumerate_file_hash(self.base_url, ch_url)

    @patch('dscan.common.VersionsFile.files_get', return_value=['misc/drupal.js'])
    @patch('dscan.common.VersionsFile.changelogs_get', return_value=['CHANGELOG.txt'])
    def test_fingerprint_correct_verb(self, patch, other_patch):
        # this needs to be a get, otherwise, how are going to get the request body?
        responses.add(responses.GET, self.base_url + 'misc/drupal.js')
        responses.add(responses.GET, self.base_url + 'CHANGELOG.txt')

        # will exception if attempts to HEAD
        self.scanner.enumerate_version(self.base_url, verb='head')

    def test_version_gt(self):
        assert self.v.version_gt("10.1", "9.1")
        assert self.v.version_gt("5.23", "5.9")
        assert self.v.version_gt("5.23.10", "5.23.9")

        assert self.v.version_gt("10.1", "10.1") == False
        assert self.v.version_gt("9.1", "10.1") == False
        assert self.v.version_gt("5.9", "5.23") == False
        assert self.v.version_gt("5.23.8", "5.23.9") == False

    def test_version_gt_different_length(self):
        assert self.v.version_gt("10.0.0.0.0", "10") == False
        assert self.v.version_gt("10", "10.0.0.0.0.0") == False
        assert self.v.version_gt("10.0.0.0.1", "10") == True

    def test_version_gt_diff_minor(self):
        # added after failures parsing SS versions.
        assert self.v.version_gt("3.0.9", "3.1.5") == False
        assert self.v.version_gt("3.0.11", "3.1.5") == False
        assert self.v.version_gt("3.0.10", "3.1.5") == False
        assert self.v.version_gt("3.0.8", "3.1.5") == False
        assert self.v.version_gt("3.0.7", "3.1.5") == False
        assert self.v.version_gt("3.0.6", "3.1.5") == False

    def test_version_gt_rc(self):
        assert self.v.version_gt("3.1.7", "3.1.7-rc1")
        assert self.v.version_gt("3.1.7", "3.1.7-rc2")
        assert self.v.version_gt("3.1.7", "3.1.7-rc3")
        assert self.v.version_gt("3.1.8", "3.1.7-rc1")
        assert self.v.version_gt("4", "3.1.7-rc1")

        assert self.v.version_gt("3.1.7-rc1", "3.1.7-rc1") == False
        assert self.v.version_gt("3.1.7-rc1", "3.1.7") == False
        assert self.v.version_gt("3.1.6", "3.1.7-rc1") == False

    def test_version_gt_ascii(self):
        # strips all letters?
        assert self.v.version_gt('1.0a', '2.0a') == False
        assert self.v.version_gt('4.0a', '2.0a')

    def test_version_gt_edge_case(self):
        assert self.v.version_gt('8.0.0-beta6', '8.0') == False
        assert self.v.version_gt('8.0.1-beta6', '8.0')

    def test_version_gt_empty_rc(self):
        assert self.v.version_gt("3.1.8", "3.1.8-rc")
        assert self.v.version_gt("3.1.7", "3.1.8-rc") == False
        assert self.v.version_gt("3.1.8-rc", "3.1.8") == False

    def test_weird_joomla_rc(self):
        assert self.v.version_gt("2.5.28", "2.5.28.rc")
        assert self.v.version_gt("2.5.28.rc", "2.5.28") == False

        assert self.v.version_gt("2.5.0", "2.5.0_RC1")
        assert self.v.version_gt("2.5.0_RC1", "2.5.0") == False

    def test_weird_joomla_again(self):
        assert self.v.version_gt('2.5.28.rc', '2.5.28.rc2') == False
        assert self.v.version_gt('2.5.28.rc2', '2.5.28.rc')

    def test_version_highest(self):
        assert self.v.highest_version() == '7.28'

    def test_version_highest_major(self):
        res = self.v.highest_version_major(['6', '7', '8'])

        assert res['6'] == '6.15'
        assert res['7'] == '7.28'
        assert res['8'] == '7.9999'

    def test_add_to_xml(self):
        add_versions = {
            '7.31': {
                'misc/ajax.js': '30d9e08baa11f3836eca00425b550f82',
                'misc/drupal.js': '0bb055ea361b208072be45e8e004117b',
                'misc/tabledrag.js': 'caaf444bbba2811b4fa0d5aecfa837e5',
                'misc/tableheader.js': 'bd98fa07941364726469e7666b91d14d'
            },
            '6.33': {
                'misc/drupal.js': '1904f6fd4a4fe747d6b53ca9fd81f848',
                'misc/tabledrag.js': '50ebbc8dc949d7cb8d4cc5e6e0a6c1ca',
                'misc/tableheader.js': '570b3f821441cd8f75395224fc43a0ea'
            }
        }

        self.v.update(add_versions)

        highest = self.v.highest_version_major(['6', '7'])

        assert highest['6'] == '6.33'
        assert highest['7'] == '7.31'

    def test_equal_number_per_major(self):
        """
            Drupal fails hard after updating with auto updater of versions.xml
            This is because misc/tableheader.js had newer versions and not older versions of the 7.x branch.
            I've removed these manually, but if this is not auto fixed, then it
                opens up some extremely buggy-looking behaviour.

            So, in conclusion, each version should have the same number of
            files (as defined in versions.xml file) as all other versions in
            the same major branch.

            E.g. All drupal 7.x versions should reference 3 files. If one of
            them has more than 3, the detection algorithm will fail.
        """
        fails = []
        for xml_path in glob(dscan.PWD + 'plugins/*/versions.xml'):
           vf = VersionsFile(xml_path)

           controller_name = xml_path.split('/')[-2]
           controller = self.controller_get(controller_name)
           major_numbers = len(controller.update_majors[0].split('.'))

           fpvm = vf.files_per_version_major(major_numbers)

           number = 0
           for major in fpvm:
              for version in fpvm[major]:
                  nb = len(fpvm[major][version])
                  if number == 0:
                      number = nb
                      example_number = version

                  if nb != number:
                      msg = """All majors in file %s should have the same number of
                          files, and version %s has %s, versus %s on other
                          files (e.g. %s).""" % (xml_path, version, nb, number, example_number)

                      fails.append(" ".join(msg.split()))

              number = 0

        if len(fails) > 0:
            for fail in fails:
                print(fail)

            # assert False

    def test_version_exists(self):
        filename = 'misc/tableheader.js'
        file_xpath = './files/file[@url="%s"]' % filename
        file_add = self.v.root.findall(file_xpath)[0]

        assert self.v.version_exists(file_add, '6.15', 'b1946ac92492d2347c6235b4d2611184')
        assert not self.v.version_exists(file_add, '6.14', 'b1946ac92492d2347c6235b4d2611184')

    def test_version_has_changelog(self):
        v_with_changelog = VersionsFile(self.xml_file_changelog)

        assert not self.v.has_changelog()
        assert v_with_changelog.has_changelog()

    def test_narrow_skip_no_changelog(self):
        self.scanner.enumerate_file_hash = self.mock_xml(self.xml_file, "7.27")
        self.scanner.enumerate_version_changelog = m = MagicMock()

        self.scanner.vf = VersionsFile(self.xml_file)
        self.scanner.enumerate_version(self.base_url)
        assert not m.called

        self.scanner.vf = VersionsFile(self.xml_file_changelog)
        self.scanner.enumerate_version(self.base_url)
        assert m.called

    def test_narrow_down_changelog(self):
        mock_versions = ['7.26', '7.27', '7.28']

        self.scanner.vf = VersionsFile(self.xml_file_changelog)
        self.scanner.enumerate_file_hash = self.mock_xml(self.xml_file_changelog, "7.27")
        result = self.scanner.enumerate_version_changelog(self.base_url,
                mock_versions)

        assert result == ['7.27']

    def test_narrow_down_ignore_incorrect_changelog(self):
        mock_versions = ['7.26', '7.27', '7.28']

        v_changelog = VersionsFile(self.xml_file_changelog)
        self.scanner.enumerate_file_hash = self.mock_xml(self.xml_file_changelog, "7.22")
        result = self.scanner.enumerate_version_changelog(self.base_url,
                mock_versions, v_changelog)

        # Changelog is possibly outdated, can't rely on it.
        assert result == mock_versions

    def test_multiple_changelogs_or(self):
        mock_versions = ["8.0", "8.1", "8.2"]
        xml_multi_changelog = 'dscan/tests/resources/versions_multiple_changelog.xml'

        self.scanner.vf = VersionsFile(xml_multi_changelog)
        self.scanner.enumerate_file_hash = self.mock_xml(xml_multi_changelog, "8.0")
        result = self.scanner.enumerate_version_changelog(self.base_url,
                mock_versions)

        assert result == ["8.0"]

    def test_multiple_changelogs_all_fail(self):
        mock_versions = ["8.0", "8.1", "8.2"]
        xml_multi_changelog = 'dscan/tests/resources/versions_multiple_changelog.xml'

        v_changelog = VersionsFile(xml_multi_changelog)
        self.scanner.enumerate_file_hash = self.mock_xml(xml_multi_changelog,
                "7.1")
        result = self.scanner.enumerate_version_changelog(self.base_url,
                mock_versions, v_changelog)

        assert result == mock_versions

    @patch('requests.Session.head')
    def test_cms_identify_called(self, mock_head):
        mock_head().status_code = 200

        self._prepare_identify()
        with patch(self.cms_identify_module, autospec=True, return_value=True) as cim:
            try:
                self.app.run()
            except:
                pass

        assert cim.called

        args, kwargs = cim.call_args
        assert args[1] == self.base_url
        assert args[2] == 1337
        assert all(item in args[3].items() for item in self.host_header.items())

        self.assert_called_contains(mock_head, 'timeout', 1337)
        self.assert_called_contains(mock_head, 'headers', self.host_header)

    def test_cms_identify_repairs_url(self):
        url_simple = self.base_url[7:-1]
        self.clear_argv()
        self.add_argv(['scan', '-u', url_simple])

        ru_module = "dscan.common.functions.repair_url"
        ru_return = self.base_url

        with patch(self.cms_identify_module, autospec=True, return_value=True) as ci:
            with patch(ru_module, return_value=self.base_url, autospec=True) as ru:
                try:
                    self.app.run()
                except ConnectionError:
                    pass

                args, kwargs = ci.call_args
                assert ru.called
                assert args[1] == self.base_url

    def test_cms_identify_respected(self):
        self._prepare_identify()
        return_value = [False, False, True, False]

        try:
            with patch(self.process_url_module, autospec=True) as pu:
                with patch(self.cms_identify_module, side_effect=return_value, autospec=True) as cim:
                    self.app.run()
        except ConnectionError:
            pass

        assert cim.call_count == 3
        assert pu.call_count == 1

    def _prepare_identify(self, url_file=False, url_file_host=False):
        self.clear_argv()

        if url_file_host:
            self.add_argv(['scan', '-U', 'dscan/tests/resources/url_file_ip_url.txt'])
        elif url_file:
            self.add_argv(['scan', '-U', self.valid_file])
        else:
            self.add_argv(['scan', '-u', self.base_url])
            self.add_argv(['--host', 'example.com'])

        self.add_argv(['--timeout', "1337"])

    def _mock_cms_multiple(self, cms_ident_side_eff, redir_side_eff=None,
            url_file_host=False, mock_redir=True):
        if not url_file_host:
            self._prepare_identify(url_file=True)
        else:
            self._prepare_identify(url_file_host=True)

        self.p_list = []

        if mock_redir:
            if not redir_side_eff:
                def _rdr(self, url, verb, timeout, headers):
                    return url
                r_p = patch(self.redir_module, autospec=True, side_effect=_rdr)
            else:
                r_p = patch(self.redir_module, autospec=True,
                        side_effect=redir_side_eff)
            r_p.start()
            self.p_list.append(r_p)

        pui_p = patch(self.pui_module, autospec=True)
        pui = pui_p.start()
        self.p_list.append(pui_p)

        cim_p = patch(self.cms_identify_module, side_effect=cms_ident_side_eff,
                autospec=True)
        cim = cim_p.start()
        self.p_list.append(cim_p)

        return cim, pui

    def _mock_cms_multiple_stop(self):
        for p in self.p_list:
            p.stop()

        self.p_list = []

    def test_cms_identify_respected_multiple(self):
        return_value = [True, False, True, False, False, True]
        cim, pui = self._mock_cms_multiple(cms_ident_side_eff=return_value,
                url_file_host=True)

        self.app.run()

        assert cim.call_count == 6
        assert pui.call_count == 3

        args, kwargs = cim.call_args_list[0]
        assert args[1] == "http://192.168.1.1/"
        assert args[2] == 1337
        assert all(item in args[3].items() for item in self.host_header.items())

    def test_cms_identify_multiple_doesnt_crash(self):
        self._mock_cms_multiple(cms_ident_side_eff=ConnectionError)

        with patch(self.warn_module) as warn:
            self.app.run()

            assert warn.called

    def test_cms_identify(self):
        fake_hash = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        rfu = "test/topst/tust.txt"
        has_hash = 'dscan.common.versions.VersionsFile.has_hash'

        with patch(self.efh_module, autospec=True, return_value=fake_hash) as efh:
            with patch(has_hash, autospec=True, return_value=True) as hh:
                self.scanner.regular_file_url = rfu
                is_cms = self.scanner.cms_identify(self.base_url)

                args, kwargs = efh.call_args
                assert args[1] == self.base_url
                assert args[2] == rfu

                args, kwargs = hh.call_args
                assert hh.called
                assert args[1] == fake_hash
                assert is_cms == True

    def test_cms_identify_array(self):
        def _efh_side_effect(self, *args):
            if args[1] != second_url:
                raise RuntimeError
            else:
                return fake_hash

        fake_hash = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        second_url = "test/tstatat/deststat.js"
        rfu = ["test/topst/tust.txt", second_url]
        has_hash = 'dscan.common.versions.VersionsFile.has_hash'

        with patch(self.efh_module, autospec=True, side_effect=_efh_side_effect) as efh:
            with patch(has_hash, autospec=True, return_value=True) as hh:
                self.scanner.regular_file_url = rfu
                is_cms = self.scanner.cms_identify(self.base_url)

                assert efh.call_count == 2
                i = 0
                for args, kwargs in efh.call_args_list:
                    assert args[1] == self.base_url
                    assert args[2] == rfu[i]
                    i += 1

                args, kwargs = hh.call_args
                assert hh.called
                assert args[1] == fake_hash
                assert is_cms == True

    def test_cms_identify_false(self):
        rfu = "test/topst/tust.txt"
        with patch(self.efh_module, autospec=True, side_effect=RuntimeError) as m:
            self.scanner.regular_file_url = rfu
            is_cms = self.scanner.cms_identify(self.base_url)

            assert is_cms == False

    def test_cms_identify_false_notexist(self):
        fake_hash = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        rfu = "test/topst/tust.txt"
        has_hash = 'dscan.common.versions.VersionsFile.has_hash'

        with patch(self.efh_module, autospec=True, return_value=fake_hash) as efh:
            with patch(has_hash, autospec=True, return_value=False) as hh:
                self.scanner.regular_file_url = rfu
                is_cms = self.scanner.cms_identify(self.base_url)

                assert is_cms == False

    def test_has_hash(self):
        existant_hash = 'b1946ac92492d2347c6235b4d2611184'
        nonexistant_hash = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'

        assert self.v.has_hash(existant_hash) == True
        assert self.v.has_hash(nonexistant_hash) == False

    @patch('requests.Session.get')
    def test_respects_host_cms_identify(self, mock_head):
        self.scanner.cms_identify(self.base_url, headers=self.host_header)

        self.assert_called_contains(mock_head, 'headers', self.host_header)

    @patch('requests.Session.get')
    def test_respects_timeout_cms_identify(self, mock_head):
        self.scanner.cms_identify(self.base_url,
                timeout=1337)

        self.assert_called_contains(mock_head, 'timeout', 1337)

    def _mock_redir(self, url, verb, timeout, headers):
        return url

    def test_url_file_ip_url_list_identify(self):
        self.clear_argv()
        self.add_argv(['scan', '-U', 'dscan/tests/resources/url_file_ip_url.txt'])
        with patch('requests.Session.head', autospec=True) as h:
            with patch('requests.Session.get', autospec=True) as g:
                h.return_value.status_code = 200
                self.app.run()

                calls = h.call_args_list
                self.assert_called_contains_all(h, 'headers', self.host_header)
                self.assert_called_contains_all(g, 'headers', self.host_header)

    def test_redirect_identify_respects_new_host(self):
        repaired_url = 'http://example.com/'
        _, pui = self._mock_cms_multiple(cms_ident_side_eff=[True, False, False,
            False, False], redir_side_eff=[repaired_url])

        self.app.run()

        args, kwargs = pui.call_args
        url, host_header = args[1][0]

        assert url == repaired_url
        assert host_header == None

    def test_redirect_identify_ip_host_respects_new_host(self):
        repaired_url = 'http://darf.com/'
        _, pui = self._mock_cms_multiple(cms_ident_side_eff=[True, False, False,
            False, False], redir_side_eff=[repaired_url], url_file_host=True)

        self.app.run()

        args, kwargs = pui.call_args
        url, host_header = args[1][0]

        assert url == repaired_url
        assert host_header == None

    def test_redirect_identify_ip_host_respects_same_host(self):
        repaired_url = 'http://example.com/'
        _, pui = self._mock_cms_multiple(cms_ident_side_eff=[True, False, False,
            False, False], redir_side_eff=[repaired_url + "lel/"], url_file_host=True)

        self.app.run()

        args, kwargs = pui.call_args
        url, host_header = args[1][0]

        assert url == 'http://192.168.1.1/lel/'
        assert host_header == self.host_header['Host']

    def test_redirect_identify_ip_host_respects_no_redir(self):
        repaired_url = 'http://example.com/'
        _, pui = self._mock_cms_multiple(cms_ident_side_eff=[True, False, False,
            False, False], url_file_host=True)

        self.app.run()

        args, kwargs = pui.call_args
        url, host_header = args[1][0]

        assert url == 'http://192.168.1.1/'
        assert host_header == self.host_header['Host']

    @patch('requests.Session.get')
    @patch('requests.Session.head')
    def test_always_passes_header(self, mock_head, mock_get):
        self.clear_argv()
        mock_head.return_value.status_code = 200

        self.add_argv(['scan', '-e', 'v'])
        self.add_argv(['--url-file', self.valid_file_ip])
        with patch(self.cms_identify_module, autospec=True, return_value=True) as cim :
            self.app.run()

        self.assert_called_contains_all(mock_get, 'headers', self.host_header)
        self.assert_called_contains_all(mock_head, 'headers', self.host_header)

    def test_doesnt_crash_when_no_cms(self):
        self.clear_argv()
        self.add_argv(['scan', '-e', 'v', '-u', self.base_url])

        with patch(self.cms_identify_module, autospec=True, return_value=False) as m:
            try:
                self.app.run()
            except RuntimeError:
                # RuntimeError is OK bc means I handled the exception.
                pass

    def test_redirect_is_output_identify(self):
        self.clear_argv()
        self.add_argv(["scan"])
        self.add_argv(['-u', self.base_url, '--method', 'forbidden'])

        with patch(self.redir_module, return_value=self.base_url_https) as dr:
            with patch('dscan.common.output.StandardOutput.echo') as e:
                try:
                    self.app.run()
                except ConnectionError:
                    pass

                args, kwargs = e.call_args_list[0]
                outputs_redirect_url = self.base_url_https in args[0]
                assert outputs_redirect_url

            assert dr.called

    def test_version_highest_not_present_multiple_digit(self):
        add_versions = {
            '3.1.31': {
                'misc/ajax.js': '30d9e08baa11f3836eca00425b550f82',
                'misc/drupal.js': '0bb055ea361b208072be45e8e004117b',
                'misc/tabledrag.js': 'caaf444bbba2811b4fa0d5aecfa837e5',
                'misc/tableheader.js': 'bd98fa07941364726469e7666b91d14d'
            },
            '3.2.12': {
                'misc/drupal.js': '1904f6fd4a4fe747d6b53ca9fd81f848',
                'misc/tabledrag.js': '50ebbc8dc949d7cb8d4cc5e6e0a6c1ca',
                'misc/tableheader.js': '570b3f821441cd8f75395224fc43a0ea'
            }
        }

        self.v.update(add_versions)

        highest = self.v.highest_version_major(['3.1', '3.2', '3.3'])

        assert highest['3.1'] == '3.1.31'
        assert highest['3.2'] == '3.2.12'
        assert highest['3.3'] == '3.2.9999'


