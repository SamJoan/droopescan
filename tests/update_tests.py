from cement.utils import test
from common import VersionsFile
from common.testutils import decallmethods
from common.update_api import github_tags_newer, github_repo, _github_normalize
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
    path = UW + "drupal/drupal/"
    gr = None

    def setUp(self):
        super(UpdateTests, self).setUp()
        self.add_argv(['update'])
        self.updater = Update()
        self._init_scanner()

        self.gr = GitRepo(self.drupal_gh, self.plugin_name)

        os_mock = ['os.makedirs', 'subprocess.call', 'subprocess.check_output']
        self.patchers = []
        for mod in os_mock:
            mod_name = mod.split('.')[-1]

            ret_val = None
            if mod_name == 'call':
                ret_val = 0

            if ret_val != None:
                self.patchers.append(patch(mod, return_value=ret_val))
            else:
                self.patchers.append(patch(mod))

            attr_name = "mock_%s" % (mod_name)
            setattr(self, attr_name, self.patchers[-1].start())

    def tearDown(self):
        for p in self.patchers:
            p.stop()

    def gh_mock(self):
        # github_response.html has 7.34 & 6.34 as the latest tags.
        gh_resp = open('tests/resources/github_response.html').read()
        responses.add(responses.GET, 'https://github.com/drupal/drupal/releases', body=gh_resp)
        responses.add(responses.GET, 'https://github.com/silverstripe/silverstripe-framework/releases')

    def test_update_calls_plugin(self):
        self.gh_mock()
        m = self.mock_controller('drupal', 'update_version_check', return_value=False)
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

    def test_github_tag_newer(self):
        self.gh_mock()
        with patch('common.update_api.VersionsFile') as vf:
            vf().highest_version_major.return_value = {'6': '6.34', '7': '7.33'}
            assert github_tags_newer('drupal/drupal/', 'not_a_real_file.xml', ['6', '7'])

            vf().highest_version_major.return_value = {'6': '6.34', '7': '7.34'}
            assert not github_tags_newer('drupal/drupal/', 'not_a_real_file.xml', ['6', '7'])

            vf().highest_version_major.return_value = {'6': '6.33', '7': '7.34'}
            assert github_tags_newer('drupal/drupal/', 'not_a_real_file.xml', ['6', '7'])

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
        assert gr.path == path_on_disk

    def test_create_pull(self):
        with patch('common.update_api.GitRepo.clone') as clone:
            with patch('os.path.isdir', return_value=False) as isdir:
                self.gr.init()

                assert clone.called
                assert isdir.called

        with patch('common.update_api.GitRepo.pull') as pull:
            with patch('os.path.isdir', return_value=True) as isdir:
                self.gr.init()

                assert pull.called
                assert isdir.called

    def test_clone_creates_dir(self):
        self.gr.clone()
        args, kwargs = self.mock_makedirs.call_args
        assert args[0] == './update-workspace/drupal'
        assert args[1] == '0700'

        self.mock_makedirs.side_effect = OSError()
        self.gr.clone()

    def test_clone_func(self):
        self.gr.clone()

        args, kwargs = self.mock_call.call_args
        expected = tuple([['git', 'clone', self.drupal_gh, self.path]])

        assert args == expected

    def test_pull_func(self):
        self.gr.pull()

        args, kwargs = self.mock_call.call_args

        expected = tuple([['git', 'pull']])

        assert args == expected
        assert kwargs['cwd'] == self.path

    @test.raises(RuntimeError)
    def test_tags_newer_exc(self):
        tags_get_ret = ['7.34', '6.34', '7.33', '6.33', '8.1']
        update_majors = ['6', '7']
        with patch('common.update_api.VersionsFile') as vf:
            with patch('common.update_api.GitRepo.tags_get') as tg:
                vf.highest_version_major.return_value = {'6': '6.34', '7': '7.34'}
                tg.return_value = tags_get_ret
                exceptioned = False

                # No new tags should result in exception.
                self.gr.tags_newer(vf, update_majors)

    def test_tags_newer_func(self):
        tags_get_ret = ['7.34', '6.34', '7.33', '6.33', '8.1']
        update_majors = ['6', '7']
        with patch('common.update_api.VersionsFile') as vf:
            with patch('common.update_api.GitRepo.tags_get') as tg:
                vf.highest_version_major.return_value = {'6': '6.33', '7': '7.33'}
                tg.return_value = tags_get_ret

                out = self.gr.tags_newer(vf, update_majors)

                args, kwargs = vf.highest_version_major.call_args
                assert args[0] == update_majors
                assert '6.34' in out
                assert '7.34' in out

                vf.highest_version_major.return_value = {'6': '6.32', '7': '7.33'}
                out = self.gr.tags_newer(vf, update_majors)
                assert '6.33' in out
                assert '6.34' in out
                assert '7.34' in out

    def test_tags_get_func(self):
        tags_get_ret = ['7.34', '6.34', '7.33', '6.33', '8.1']
        tags_content = open('tests/resources/git_tag_output.txt').read()
        self.mock_check_output.return_value = tags_content

        out = self.gr.tags_get()
        assert len(out) == len(tags_get_ret)
        for t in tags_get_ret:
            assert t in out

    def test_drupal_update_calls_gh_update(self):
        with patch('plugins.drupal.github_tags_newer') as m:
            self.scanner.update_version_check()

            assert m.called

    def test_drupal_update(self):
        with patch('common.update_api.github_repo') as m:
            self.scanner.update_version()

            assert m.called

    def test_drupal_update_calls_tags_newer(self):
        with patch('plugins.drupal.GitRepo.tags_newer') as m:
            self.scanner.update_version()

            args, kwargs = m.call_args
            assert isinstance(args[0], VersionsFile)
            assert args[1] == self.scanner._update_majors

    def test_drupal_calls_hashes_get(self):
        vf = MagicMock()

        new_versions = ['7.34', '6.34']
        ret_val = (self.gr, vf, new_versions)

        with patch('plugins.drupal.github_repo_new', return_value=ret_val) as m:
            with patch('plugins.drupal.GitRepo.tag_checkout') as tc:
                with patch('plugins.drupal.GitRepo.hashes_get') as hg:
                    self.scanner.update_version()
                    assert len(tc.call_args_list) == 2
                    assert len(hg.call_args_list) == 2

                    for call in hg.call_args_list:
                        args, kwargs = call
                        assert args[0] in new_versions
                        assert args[1] == vf
                        assert isinstance(args[2], GitRepo)

    def test_tag_checkout_func(self):
        assert False

    def test_hashes_get(self):
        assert False


