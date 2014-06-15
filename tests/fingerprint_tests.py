from common.testutils import file_len, decallmethods
from tests import BaseTest
import responses

@decallmethods(responses.activate)
class FingerprintTests(BaseTest):
    def test_fingerprint_warns_if_changelog(self):
        assert False

    def test_drupal_versions_xml_validates(self):
        assert False
