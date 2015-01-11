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


    def setUp(self):
        super(FingerprintTests, self).setUp()
        self.add_argv(['scan', 'drupal'])
        self.add_argv(['--method', 'forbidden'])
        self.add_argv(self.param_version)
        self._init_scanner()
        self.v = VersionsFile(self.xml_file)

    def test_integration(self):
        assert False
