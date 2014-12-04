from cement.utils import test
from common import VersionsFile
from common.testutils import decallmethods
from common.update_api import github_tag_newer, github_repo, _github_normalize
from common.update_api import GitRepo
from common.update_api import GH, UW
from mock import patch, MagicMock
from plugins.update import Update
from tests import BaseTest
import common
import responses

@decallmethods(responses.activate)
class UpdateTests(BaseTest):

    drupal_repo_path = 'drupal/drupal/'
    drupal_gh = '%s%s' % (GH, drupal_repo_path)
    plugin_name = 'drupal'

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

    def test_github_repo(self):
        with patch('common.update_api.GitRepo.__init__', return_value=None) as gri:
            with patch('common.update_api.GitRepo.init') as grii:
                returned_gh = github_repo(self.drupal_repo_path, self.plugin_name)
                args, kwargs = gri.call_args

                assert args[0] == self.drupal_gh
                assert args[1] == self.plugin_name

                assert gri.called
                assert grii.called

                assert isinstance(returned_gh, GitRepo)

    def test_normalize_repo(self):
        expected = 'drupal/drupal/'
        assert _github_normalize("/drupal/drupal/") == expected
        assert _github_normalize("/drupal/drupal") == expected
        assert _github_normalize("drupal/drupal") == expected
        assert _github_normalize("/drupal/drupal/") == expected

    def test_gr_init(self):
        gr = GitRepo(self.drupal_gh, self.plugin_name)
        repo_name = self.drupal_gh.split('/')[-2:][0] + '/'

        path_on_disk = '%s%s%s' % (UW, self.plugin_name + "/", repo_name)

        assert gr._clone_url == self.drupal_gh
        assert gr._path == path_on_disk

