from cement.utils import test
from common.testutils import decallmethods, xml_validate
from common import VersionsFile
from glob import glob
from lxml import etree
from mock import patch, MagicMock
from plugins.drupal import Drupal
from requests.exceptions import ConnectionError
from tests import BaseTest
import hashlib
import requests
import responses

@decallmethods(responses.activate)
class FingerprintTests(BaseTest):
    '''
        Tests related to version fingerprinting for all plugins.
    '''

    xml_file_changelog = 'tests/resources/versions_with_changelog.xml'

    def setUp(self):
        super(FingerprintTests, self).setUp()
        self.add_argv(['scan', 'drupal'])
        self.add_argv(['--method', 'forbidden'])
        self.add_argv(self.param_version)
        self._init_scanner()
        self.v = VersionsFile(self.xml_file)

    @patch('common.VersionsFile.files_get', return_value=['misc/drupal.js'])
    @patch('common.VersionsFile.changelogs_get', return_value=['CHANGELOG.txt'])
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
        for xml_path in glob('plugins/*/versions.xml'):
            xml_validate(xml_path, self.versions_xsd)

    def test_determines_version(self):
        real_version = '7.26'
        self.scanner.enumerate_file_hash = self.mock_xml(self.xml_file, real_version)

        version, is_empty = self.scanner.enumerate_version(self.base_url, self.xml_file)

        assert version[0] == real_version
        assert is_empty == False

    def test_determines_version_similar(self):
        real_version = '6.15'
        self.scanner.enumerate_file_hash = self.mock_xml(self.xml_file, real_version)
        returned_version, is_empty = self.scanner.enumerate_version(self.base_url, self.xml_file)

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

    @patch('common.VersionsFile.files_get', return_value=['misc/drupal.js'])
    @patch('common.VersionsFile.changelogs_get', return_value=['CHANGELOG.txt'])
    def test_fingerprint_correct_verb(self, patch, other_patch):
        # this needs to be a get, otherwise, how are going to get the request body?
        responses.add(responses.GET, self.base_url + 'misc/drupal.js')
        responses.add(responses.GET, self.base_url + 'CHANGELOG.txt')

        # will exception if attempts to HEAD
        self.scanner.enumerate_version(self.base_url,
                self.scanner.versions_file, verb='head')

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
        for xml_path in glob('plugins/*/versions.xml'):
           vf = VersionsFile(xml_path)

           if 'silverstripe' in xml_path:
               major_numbers = 2
           else:
               major_numbers = 1

           fpvm = vf.files_per_version_major(major_numbers)

           number = 0
           for major in fpvm:
              for version in fpvm[major]:
                  nb = len(fpvm[major][version])
                  if number == 0:
                      number = nb

                  if nb != number:
                      msg = """All majors should have the same number of
                          files, and version %s has %s, versus %s on other
                          files.""" % (version, nb, number)

                      fails.append(" ".join(msg.split()))

              number = 0

        if len(fails) > 0:
            for fail in fails:
                print(fail)

            assert False

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

        self.scanner.enumerate_version(self.base_url, self.xml_file)
        assert not m.called

        self.scanner.enumerate_version(self.base_url, self.xml_file_changelog)
        assert m.called

    def test_narrow_down_changelog(self):
        mock_versions = ['7.26', '7.27', '7.28']

        v_changelog = VersionsFile(self.xml_file_changelog)
        self.scanner.enumerate_file_hash = self.mock_xml(self.xml_file_changelog, "7.27")
        result = self.scanner.enumerate_version_changelog(self.base_url,
                mock_versions, v_changelog)

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
        xml_multi_changelog = 'tests/resources/versions_multiple_changelog.xml'

        v_changelog = VersionsFile(xml_multi_changelog)
        self.scanner.enumerate_file_hash = self.mock_xml(xml_multi_changelog, "8.0")
        result = self.scanner.enumerate_version_changelog(self.base_url,
                mock_versions, v_changelog)

        assert result == ["8.0"]

    def test_multiple_changelogs_all_fail(self):
        mock_versions = ["8.0", "8.1", "8.2"]
        xml_multi_changelog = 'tests/resources/versions_multiple_changelog.xml'

        v_changelog = VersionsFile(xml_multi_changelog)
        self.scanner.enumerate_file_hash = self.mock_xml(xml_multi_changelog,
                "7.1")
        result = self.scanner.enumerate_version_changelog(self.base_url,
                mock_versions, v_changelog)

        assert result == mock_versions
