from common.testutils import decallmethods, xml_validate
from plugins.drupal import Drupal
from tests import BaseTest
import responses

@decallmethods(responses.activate)
class FingerprintTests(BaseTest):
    """
        Tests related to version fingerprinting for all plugins.
    """

    versions_xsd = "common/versions.xsd"

    def test_fingerprint_warns_if_changelog(self):
        assert False

    def test_xml_validates_drupal(self):
        drupal = Drupal()

        xml_validate(drupal.versions_file, self.versions_xsd)
