import unittest
from mock import patch, MagicMock
from dscan.common import plugins_util
from dscan.plugins.internal.base_plugin import BasePlugin

class TestPlugin(BasePlugin):
    class Meta:
        label = 'test_plugin'
    
    regular_file_url = 'test_url'
    update_majors = ['1.0']
    
    can_enumerate_plugins = True
    can_enumerate_themes = True
    can_enumerate_interesting = True
    can_enumerate_version = True
    
    interesting_urls = ['test']

class PluginsUtilTests(unittest.TestCase):
    
    def setUp(self):
        # Reset globals
        plugins_util._base_plugins = None
        plugins_util._rfu = None
        plugins_util._vf = None

    @patch('dscan.common.plugins_util.plugins_base_get')
    def test_get_rfu(self, mock_plugins_base_get):
        mock_plugin = MagicMock()
        mock_plugin.regular_file_url = "test_url"
        mock_plugins_base_get.return_value = [mock_plugin]
        
        rfu = plugins_util.get_rfu()
        self.assertEqual(rfu, ["test_url"])
        
        # Test caching
        mock_plugins_base_get.return_value = []
        rfu_cached = plugins_util.get_rfu()
        self.assertEqual(rfu_cached, ["test_url"])

    @patch('dscan.common.plugins_util.plugins_base_get')
    def test_get_rfu_list(self, mock_plugins_base_get):
        mock_plugin = MagicMock()
        mock_plugin.regular_file_url = ["test_url_1", "test_url_2"]
        mock_plugins_base_get.return_value = [mock_plugin]
        
        rfu = plugins_util.get_rfu()
        self.assertEqual(rfu, ["test_url_1", "test_url_2"])

    def test_plugin_get_rfu(self):
        mock_plugin = MagicMock()
        mock_plugin.regular_file_url = "test_url"
        
        rfu = plugins_util.plugin_get_rfu(mock_plugin)
        self.assertEqual(rfu, ["test_url"])
        
        mock_plugin.regular_file_url = ["test_url_list"]
        rfu = plugins_util.plugin_get_rfu(mock_plugin)
        self.assertEqual(rfu, ["test_url_list"])

    @patch('dscan.common.plugins_util.plugins_base_get')
    def test_plugin_get(self, mock_plugins_base_get):
        mock_plugin = MagicMock()
        mock_plugin.Meta.label = "test_plugin"
        mock_plugins_base_get.return_value = [mock_plugin]
        
        plugin = plugins_util.plugin_get("test_plugin")
        self.assertEqual(plugin, mock_plugin)
        
        with self.assertRaises(RuntimeError):
            plugins_util.plugin_get("non_existent_plugin")

    @patch('dscan.common.plugins_util.file_len')
    @patch('dscan.common.plugins_util.VersionsFile')
    def test_plugin_class_init(self, mock_versions_file, mock_file_len):
        mock_file_len.return_value = 10
        mock_vf_instance = mock_versions_file.return_value
        mock_vf_instance.highest_version_major.return_value = {'1': '1.0.0'}
        
        # Mocking the PluginClass passed to __init__
        # It needs to return a plugin instance when instantiated
        MockPluginClass = MagicMock(return_value=TestPlugin())
        
        plugin_wrapper = plugins_util.Plugin(MockPluginClass)
        
        self.assertEqual(plugin_wrapper.name, 'test_plugin')
        self.assertTrue(plugin_wrapper.plugins_can_enumerate)
        self.assertEqual(plugin_wrapper.plugins_wordlist_size, 10)
        self.assertTrue(plugin_wrapper.themes_can_enumerate)
        self.assertEqual(plugin_wrapper.themes_wordlist_size, 10)
        self.assertTrue(plugin_wrapper.interesting_can_enumerate)
        self.assertTrue(plugin_wrapper.version_can_enumerate)
        self.assertEqual(plugin_wrapper.version_highest, '1.0.0')

    @patch('dscan.common.plugins_util.plugins_base_get')
    @patch('dscan.common.plugins_util.VersionsFile')
    def test_get_vf(self, mock_versions_file, mock_plugins_base_get):
        mock_plugin = MagicMock()
        mock_plugin.Meta.label = "test_plugin"
        mock_plugins_base_get.return_value = [mock_plugin]
        
        vf = plugins_util.get_vf()
        self.assertIn("test_plugin", vf)
        self.assertTrue(mock_versions_file.called)
        
        # Test caching
        mock_plugins_base_get.return_value = []
        vf_cached = plugins_util.get_vf()
        self.assertEqual(vf, vf_cached)

    @patch('dscan.common.plugins_util.get_vf')
    def test_plugin_get_vf(self, mock_get_vf):
        mock_plugin = MagicMock()
        mock_plugin.Meta.label = "test_plugin"
        mock_get_vf.return_value = {"test_plugin": "test_vf"}
        
        vf = plugins_util.plugin_get_vf(mock_plugin)
        self.assertEqual(vf, "test_vf")

    @patch('dscan.common.plugins_util.subprocess.check_output')
    def test_plugin_file_mtime(self, mock_check_output):
        mock_check_output.return_value = b"2 days ago\n"
        
        # Instantiate Plugin with a mock PluginClass that returns None to skip __init__ logic
        # Actually Plugin.__init__ creates an instance of PluginClass. 
        # If we pass a mock that returns None, Plugin.__init__ might fail or do nothing if checks `if plugin:`
        
        # Let's use a mock class that returns a minimal mock object
        mock_plugin_instance = MagicMock()
        mock_plugin_instance.can_enumerate_plugins = False
        mock_plugin_instance.can_enumerate_themes = False
        mock_plugin_instance.can_enumerate_interesting = False
        mock_plugin_instance.can_enumerate_version = False
        MockPluginClass = MagicMock(return_value=mock_plugin_instance)
        
        plugin_wrapper = plugins_util.Plugin(MockPluginClass)
        mtime = plugin_wrapper.file_mtime("some/path")
        
        self.assertEqual(mtime, b"2 days ago")
        mock_check_output.assert_called_with(['git', 'log', '-1', '--format=%cr', 'some/path'])

    @patch('dscan.common.plugins_util.plugins_base_get')
    def test_plugins_get(self, mock_plugins_base_get):
        # plugins_get iterates over plugins_base_get() and instantiates Plugin() for each.
        # plugins_base_get returns a list of Plugin classes (Controller subclasses)
        
        mock_plugin_class = MagicMock()
        mock_plugin_instance = mock_plugin_class.return_value
        mock_plugin_instance._meta.label = 'test_plugin'
        # minimal attributes
        mock_plugin_instance.can_enumerate_plugins = False
        mock_plugin_instance.can_enumerate_themes = False
        mock_plugin_instance.can_enumerate_interesting = False
        mock_plugin_instance.can_enumerate_version = False
        
        mock_plugins_base_get.return_value = [mock_plugin_class]
        
        result = plugins_util.plugins_get()
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], plugins_util.Plugin)
        self.assertEqual(result[0].name, 'test_plugin')

