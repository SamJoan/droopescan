from cement.utils import test
from common.testutils import decallmethods, xml_validate
from mock import patch, MagicMock
from plugins.drupal import Drupal
from requests.exceptions import ConnectionError
from tests import BaseTest
from lxml import etree
import responses

@decallmethods(responses.activate)
class FingerprintTests(BaseTest):
    """
        Tests related to version fingerprinting for all plugins.
    """

    versions_xsd = "common/versions.xsd"
    xml_file = "tests/versions.xml"

    class MockHash():
        files = None
        def mock_func(self, *args, **kwargs):
            url = kwargs['file_url']
            return self.files[url]

    def setUp(self):
        super(FingerprintTests, self).setUp()
        self.add_argv(["drupal"])
        self.add_argv(["--method", "forbidden"])
        self.add_argv(self.param_version)
        self.scanner = Drupal()

    def mock_xml(self, xml_file, version_to_mock):
        """
            generates all mock data, and patches Drupal.get_hash
        """
        with open(xml_file) as f:
            doc = etree.fromstring(f.read())
            files_xml = doc.xpath("//cms/files/file")

            files = {}
            for file in files_xml:
                url = file.get("url")
                versions = file.xpath("version")
                for file_version in versions:
                    version_number = file_version.get("nb")
                    md5 = file_version.get("md5")

                    if version_number == version_to_mock:
                        files[url] = md5

        mock_hash = self.MockHash()
        mock_hash.files = files
        mock = MagicMock(side_effect=mock_hash.mock_func)

        return mock

    @patch('common.warn')
    def test_fingerprint_warns_if_changelog(self, m):
        self.respond_several(self.base_url + "%s", {200: ["CHANGELOG.txt"]})
        self.app.run()

        assert m.called, "should have warned about changelog being present."

    def test_fingerprint_respects_verb(self):
        assert False

    def test_xml_validates_drupal(self):
        drupal = Drupal()

        xml_validate(drupal.versions_file, self.versions_xsd)

    def test_determines_version(self):
        # mock the URLs needed
        real_version = "7.26"
        self.scanner.enumerate_file_hash = self.mock_xml(self.xml_file, real_version)

        version, certainty = self.scanner.enumerate_version(self.base_url, self.xml_file)

        assert version == real_version

    @test.raises(ConnectionError)
    def test_calls_version(self):
        self.app.run()


