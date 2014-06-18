from cement.utils import test
from common.testutils import decallmethods, xml_validate
from mock import patch
from plugins.drupal import Drupal
from requests.exceptions import ConnectionError
from tests import BaseTest
import responses

@decallmethods(responses.activate)
class FingerprintTests(BaseTest):
    """
        Tests related to version fingerprinting for all plugins.
    """

    versions_xsd = "common/versions.xsd"

    def setUp(self):
        super(FingerprintTests, self).setUp()
        self.add_argv(["drupal"])
        self.add_argv(["--method", "forbidden"])
        self.add_argv(self.param_version)
        self.scanner = Drupal()

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
        assert False

    @test.raises(ConnectionError)
    def test_calls_version(self):
        self.app.run()


