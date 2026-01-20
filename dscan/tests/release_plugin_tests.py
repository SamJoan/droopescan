import unittest
from mock import patch, MagicMock
from dscan.plugins.release import Release, c

class ReleasePluginTests(unittest.TestCase):
    
    @patch('dscan.plugins.release.call')
    def test_c_function(self, mock_call):
        mock_call.return_value = 0
        c(['ls'])
        mock_call.assert_called_with(['ls'])
        
        mock_call.return_value = 1
        with self.assertRaises(RuntimeError):
            c(['ls'])

    @patch('dscan.plugins.release.c')
    @patch('dscan.plugins.release.check_output')
    @patch('dscan.plugins.release.ra')
    @patch('dscan.plugins.release.call') # for git push
    def test_ship(self, mock_call_push, mock_ra, mock_check_output, mock_c):
        mock_check_output.return_value = b'development'
        mock_ra.changelog_modify.return_value = '1.0.0'
        
        release_plugin = Release()
        release_plugin.app = MagicMock()
        release_plugin.app.pargs.skip_external = False
        
        release_plugin.ship()
        
        mock_ra.check_pypirc.assert_called()
        mock_ra.test_all.assert_called_with(False)
        mock_ra.changelog_modify.assert_called()
        
        # Verify git commands were called via c()
        # We can't easily check order without assert_has_calls for all mocks combined, 
        # but we can check if they were called.
        
        # git add .
        mock_c.assert_any_call(['git', 'add', '.'])
        # git commit
        mock_c.assert_any_call(['git', 'commit', '-m', "Tagging version '1.0.0'"])
        # git checkout master
        mock_c.assert_any_call(['git', 'checkout', 'master'])
        # git merge development
        mock_c.assert_any_call(['git', 'merge', b'development'])
        # git tag
        mock_c.assert_any_call(['git', 'tag', '1.0.0'])
        # git clean
        mock_c.assert_any_call(['git', 'clean', '-dXff'])
        # python setup.py sdist upload ...
        # 1.0.0 matches regex ^[0-9.]*$ so repo should be pypi
        mock_c.assert_any_call(['python', 'setup.py', 'sdist', 'upload', '-r', 'pypi'])
        
        # git push calls
        mock_call_push.assert_any_call('git remote | xargs -l git push --all', shell=True)
        
        # Finally block: checkout development
        mock_c.assert_any_call(['git', 'checkout', 'development'])
        mock_c.assert_any_call(['git', 'merge', 'master'])

    @patch('dscan.plugins.release.Release.ship')
    def test_default(self, mock_ship):
        release_plugin = Release()
        release_plugin.default()
        mock_ship.assert_called()

