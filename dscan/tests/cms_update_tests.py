import unittest
from mock import patch, MagicMock
from dscan.plugins.joomla import Joomla
from dscan.plugins.moodle import Moodle

class CmsUpdateTests(unittest.TestCase):
    
    @patch('dscan.common.update_api.github_tags_newer')
    def test_joomla_update_version_check(self, mock_github_tags_newer):
        mock_github_tags_newer.return_value = True
        
        joomla = Joomla()
        # Mock versions_file attribute which is initialized in BasePlugin.__init__
        # but since we are just instantiating without running app logic, we might need to mock it if used.
        # Joomla inherits BasePlugin which calls BasePluginInternal which sets versions_file
        # BasePlugin.__init__ sets self.versions_file path string.
        
        result = joomla.update_version_check()
        
        self.assertTrue(result)
        mock_github_tags_newer.assert_called()
        args, kwargs = mock_github_tags_newer.call_args
        self.assertEqual(args[0], 'joomla/joomla-cms/')
        self.assertEqual(kwargs['update_majors'], joomla.update_majors)

    @patch('dscan.common.update_api.github_repo_new')
    def test_joomla_update_version(self, mock_github_repo_new):
        mock_gr = MagicMock()
        mock_versions_file = MagicMock()
        mock_new_tags = ['3.9.0', '3.10.0-alpha1'] # one valid, one alpha
        
        mock_github_repo_new.return_value = (mock_gr, mock_versions_file, mock_new_tags)
        
        mock_gr.hashes_get.return_value = 'some_hashes'
        
        joomla = Joomla()
        # Capture print output? Or just let it print.
        
        updated_vf = joomla.update_version()
        
        self.assertEqual(updated_vf, mock_versions_file)
        
        # Check that tag_checkout was called for 3.9.0 but not for alpha
        mock_gr.tag_checkout.assert_called_with('3.9.0')
        # should only be called once for valid tag
        self.assertEqual(mock_gr.tag_checkout.call_count, 1)
        
        # Check hashes update
        mock_versions_file.update.assert_called_with({'3.9.0': 'some_hashes'})

    def test_joomla_update_plugins_check(self):
        joomla = Joomla()
        self.assertFalse(joomla.update_plugins_check())

    @patch('dscan.common.update_api.github_tags_newer')
    def test_moodle_update_version_check(self, mock_github_tags_newer):
        mock_github_tags_newer.return_value = True
        moodle = Moodle()
        
        result = moodle.update_version_check()
        
        self.assertTrue(result)
        mock_github_tags_newer.assert_called()
        args, kwargs = mock_github_tags_newer.call_args
        self.assertEqual(args[0], 'moodle/moodle/')

    @patch('dscan.common.update_api.github_repo_new')
    def test_moodle_update_version(self, mock_github_repo_new):
        mock_gr = MagicMock()
        mock_versions_file = MagicMock()
        mock_new_tags = ['3.9']
        
        mock_github_repo_new.return_value = (mock_gr, mock_versions_file, mock_new_tags)
        mock_gr.hashes_get.return_value = 'some_hashes'
        
        moodle = Moodle()
        updated_vf = moodle.update_version()
        
        self.assertEqual(updated_vf, mock_versions_file)
        
        # Moodle plugin prepends 'v'
        mock_gr.tag_checkout.assert_called_with('v3.9')
        
        mock_versions_file.update.assert_called_with({'3.9': 'some_hashes'})

