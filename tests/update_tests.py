from cement.utils import test
from common import VersionsFile
from common.testutils import decallmethods
from common.update_api import github_tag_newer
from mock import patch, MagicMock
from tests import BaseTest
from plugins.update import Update
import common
import responses

@decallmethods(responses.activate)
class UpdateTests(BaseTest):

    def setUp(self):
        super(UpdateTests, self).setUp()
        self.add_argv(['update'])
        self.updater = Update()
        self._init_scanner()

    def gh_mock(self):
        # github_response.html has 7.34 & 6.34 as the latest tags.
        gh_resp = open('tests/resources/github_response.html').read()
        responses.add(responses.GET, 'https://github.com/drupal/drupal/releases', body=gh_resp)
        responses.add(responses.GET, 'https://github.com/silverstripe/silverstripe-framework/releases')

    def test_update_calls_plugin(self):
        self.gh_mock()
        m = self.mock_controller('drupal', 'update_version_check')
        self.updater.update()

        assert m.called

    def test_update_checks_and_updates(self):
        self.gh_mock()
        self.mock_controller('drupal', 'update_version_check', return_value=True)
        m = self.mock_controller('drupal', 'update_version')

        self.updater.update()

        assert m.called

    def test_update_checks_without_update(self):
        self.gh_mock()
        self.mock_controller('drupal', 'update_version_check', return_value=False)
        m = self.mock_controller('drupal', 'update_version')

        self.updater.update()

        assert not m.called

    def test_drupal_update_calls_gh_update(self):
        with patch('plugins.drupal.github_tag_newer') as m:
            self.scanner.update_version_check()

            assert m.called

    def test_github_tag_newer(self):
        self.gh_mock()
        with patch('common.update_api.VersionsFile') as vf:
            vf().highest_version_major.return_value = {'6': '6.34', '7': '7.33'}
            assert github_tag_newer('drupal/drupal/', 'not_a_real_file.xml', ['6', '7'])

            vf().highest_version_major.return_value = {'6': '6.34', '7': '7.34'}
            assert not github_tag_newer('drupal/drupal/', 'not_a_real_file.xml', ['6', '7'])

            vf().highest_version_major.return_value = {'6': '6.33', '7': '7.34'}
            assert github_tag_newer('drupal/drupal/', 'not_a_real_file.xml', ['6', '7'])

