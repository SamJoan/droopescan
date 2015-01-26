from cement.utils import test
from common import VersionsFile
from common.testutils import decallmethods
from common.update_api import GH, UW
from common.update_api import github_tags_newer, github_repo, _github_normalize
from common.update_api import GitRepo
from mock import patch, MagicMock, mock_open
from plugins.drupal import Drupal
from plugins.update import Update
from tests import BaseTest
import common
import responses

@decallmethods(responses.activate)
class UpdateTests(BaseTest):

    drupal_repo_path = 'drupal/drupal/'
    drupal_gh = '%s%s' % (GH, drupal_repo_path)
    plugin_name = 'drupal/drupal'
    path = UW + "drupal/drupal/"
    gr = None
    update_versions_xml = 'tests/resources/update_versions.xml'

    def setUp(self):
        super(UpdateTests, self).setUp()
        self.add_argv(['update'])
        self.updater = Update()
        self._init_scanner()

        self.gr = GitRepo(self.drupal_gh, self.plugin_name)

        os_mock = ['os.makedirs', 'subprocess.call', 'subprocess.check_output',
                'common.functions.md5_file',
                'common.plugins_util.plugins_base_get']
        self.patchers = []
        for mod in os_mock:
            mod_name = mod.split('.')[-1]

            ret_val = None
            if mod_name == 'call':
                ret_val = 0
            if mod_name == 'plugins_base_get':
                ret_val = [self.controller_get('drupal')]

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

    def test_update_checks_and_updates(self):
        self.gh_mock()
        self.mock_controller('drupal', 'update_version_check', return_value=True)
        m = self.mock_controller('drupal', 'update_version')

        o = mock_open()
        with patch('plugins.update.open', o, create=True):
            self.updater.update()

        assert m.called

    def test_update_checks_without_update(self):
        self.gh_mock()
        self.mock_controller('drupal', 'update_version_check', return_value=False)
        m = self.mock_controller('drupal', 'update_version')

        o = mock_open()
        with patch('plugins.update.open', o, create=True):
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
        path_on_disk = '%s%s/' % (UW, self.plugin_name)
        assert gr._clone_url == self.drupal_gh
        assert gr.path == path_on_disk

    def test_create_fetch(self):
        with patch('common.update_api.GitRepo.clone') as clone:
            with patch('os.path.isdir', return_value=False) as isdir:
                self.gr.init()

                assert clone.called
                assert isdir.called

        with patch('common.update_api.GitRepo.fetch') as fetch:
            with patch('os.path.isdir', return_value=True) as isdir:
                self.gr.init()

                assert fetch.called
                assert isdir.called

    def test_clone_creates_dir(self):
        self.gr.clone()
        expected_dir = './.update-workspace/drupal'

        args, kwargs = self.mock_makedirs.call_args
        print(args[0], expected_dir)
        assert args[0] == expected_dir
        assert args[1] == 0o700

        # Assert except block is there.
        self.mock_makedirs.side_effect = OSError()
        self.gr.clone()

    def test_clone_func(self):
        self.gr.clone()

        args, kwargs = self.mock_call.call_args
        expected = tuple([['git', 'clone', self.drupal_gh, self.path]])

        assert args == expected

    def test_fetch_func(self):
        self.gr.fetch()

        args, kwargs = self.mock_call.call_args

        expected = tuple([['git', 'fetch', '--all']])

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
        with patch('common.update_api.github_tags_newer') as m:
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
            assert args[1] == self.scanner.update_majors

    def test_drupal_calls_hashes_get(self):
        vf = MagicMock()

        new_versions = ['7.34', '6.34']
        ret_val = (self.gr, vf, new_versions)

        ret_hashes_get ={'css/css.css': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
                'javascript/main.js': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
                'css/jss.phs': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'}

        with patch('common.update_api.github_repo_new', return_value=ret_val) as m:
            with patch('plugins.drupal.GitRepo.tag_checkout') as tc:
                with patch('plugins.drupal.GitRepo.hashes_get', return_value=ret_hashes_get) as hg:
                    self.scanner.update_version()

                    tccl = tc.call_args_list
                    assert len(tc.call_args_list) == 2
                    for args, kwargs in tccl:
                        assert args[0] in new_versions

                    hgcl = hg.call_args_list
                    assert len(hg.call_args_list) == 2
                    for args, kwargs in hgcl:
                        assert args[0] == vf
                        assert args[1] == self.scanner.update_majors

        version = '7.34'
        expected = tuple([['git', 'checkout', version]])
        self.gr.tag_checkout(version)

        args, kwargs = self.mock_call.call_args
        assert args == expected
        assert kwargs['cwd'] == self.gr.path

    def test_hashes_get_func(self):
        md5 = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        files = ['javascript/main.js', 'css/css.css', 'css/jss.phs']
        self.mock_md5_file.return_value = md5

        with patch('common.update_api.VersionsFile') as vf:
            vf.files_get_all.return_value = files
            self.gr.hashes_get(vf, self.scanner.update_majors)

            assert vf.files_get_all.called
            assert len(self.mock_md5_file.call_args_list) == len(files)
            for call in self.mock_md5_file.call_args_list:
                args, kwargs = call

                in_there = False
                for f in files:
                    if args[0].endswith(f):
                        in_there = True
                        break

                assert UW in args[0]
                assert in_there

    def test_update_calls_plugin(self):
        md5 = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        files = ['misc/drupal.js', 'misc/tabledrag.js', 'misc/ajax.js']
        self.mock_md5_file.return_value = md5

        vf = VersionsFile(self.update_versions_xml)
        versions = ['7.34', '6.34']
        ret_val = (self.gr, vf, versions)

        with patch('common.update_api.github_repo_new', return_value=ret_val) as m:
            fpv_before = vf.files_per_version()
            out = self.scanner.update_version()
            fpv_after = vf.files_per_version()

            assert len(fpv_before) == len(fpv_after) - len(versions)
            for v in versions:
                assert v in fpv_after
                assert fpv_after[v] == files

    def test_files_get_all_chlg(self):
        changelog_file = 'CHANGELOG.txt'
        vf = VersionsFile(self.update_versions_xml)
        files = vf.files_get()
        files_all = vf.files_get_all()

        assert len(files) == len(files_all) - 1
        assert changelog_file in files_all
        assert not changelog_file in files

    def test_updates_changelog(self):
        weird_hash = '13371337133713371337133713371337'
        vf = VersionsFile(self.update_versions_xml)

        hashes = {
            '6.34': {
                'misc/ajax.js': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
                'CHANGELOG.txt': weird_hash,
                'misc/drupal.js': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
                'misc/tabledrag.js': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
            }
        }

        vf.update(hashes)

        out = vf.str_pretty()
        assert weird_hash in str(out)

    def test_writes_vf(self):
        vf = MagicMock()
        xml = '<cms>lalala'
        vf.str_pretty.return_value = xml

        o = mock_open()
        with patch('plugins.update.open', o, create=True):

            uvc = self.mock_controller('drupal', 'update_version_check', return_value=True)
            uv = self.mock_controller('drupal', 'update_version', return_value=vf)

            self.updater.update()

            args, kwargs = o.call_args
            assert args[0] == self.scanner.versions_file
            assert args[1] == 'w'

            args, kwargs = o().write.call_args
            assert args[0] == xml

    def test_writes_valid_xml(self):
        self.mock_controller('drupal', 'update_version_check', return_value=True)
        self.mock_controller('drupal', 'update_version')

        o = mock_open()
        with patch('plugins.update.open', o, create=True):
            with patch('plugins.update.Update.is_valid', return_value=False) as iv:
                self.updater.update()

                args, kwargs = iv.call_args

                assert iv.called
                assert not o().write.called

