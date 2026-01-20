import unittest
from mock import patch, MagicMock, mock_open
import os
from dscan.plugins.tests import Tests, recursive_grep, which
import dscan.plugins.tests

class TestCommandTests(unittest.TestCase):
    
    def test_recursive_grep(self):
        with patch('os.listdir', return_value=['test_file.py']):
            with patch('dscan.plugins.tests.open', mock_open(read_data='def target_function():\n'), create=True):
                result = recursive_grep('/tmp/', 'target_function')
                self.assertEqual(result, 'test_file.py')
            
    def test_recursive_grep_not_found(self):
        with patch('os.listdir', return_value=['test_file.py']):
            with patch('dscan.plugins.tests.open', mock_open(read_data='def other_function():\n'), create=True):
                result = recursive_grep('/tmp/', 'target_function')
                self.assertIsNone(result)

    def test_which_absolute_path(self):
        with patch('os.path.isfile', return_value=True):
            with patch('os.access', return_value=True):
                result = which('/bin/ls')
                self.assertEqual(result, '/bin/ls')

    def test_which_in_path(self):
        with patch('os.environ', {"PATH": "/bin:/usr/bin"}):
            with patch('os.path.isfile') as mock_isfile:
                with patch('os.access', return_value=True):
                    # Make /usr/bin/program return True
                    def side_effect(path):
                        return path == '/usr/bin/program'
                    mock_isfile.side_effect = side_effect
                    
                    result = which('program')
                    self.assertEqual(result, '/usr/bin/program')

    @patch('dscan.plugins.tests.call')
    @patch('dscan.plugins.tests.which')
    @patch('sys.exit')
    def test_default_no_args(self, mock_exit, mock_which, mock_call):
        mock_which.return_value = '/usr/bin/nosetests'
        mock_call.return_value = 0
        
        test_plugin = Tests()
        test_plugin.app = MagicMock()
        test_plugin.app.pargs.single_test = None
        test_plugin.app.pargs.with_coverage = False
        
        test_plugin.default()
        
        mock_call.assert_called()
        args, kwargs = mock_call.call_args
        self.assertEqual(args[0][0], '/usr/bin/nosetests')
        self.assertNotIn('--with-coverage', args[0])
        mock_exit.assert_called_with(0)

    @patch('dscan.plugins.tests.call')
    @patch('dscan.plugins.tests.which')
    @patch('sys.exit')
    def test_default_with_coverage(self, mock_exit, mock_which, mock_call):
        mock_which.return_value = '/usr/bin/nosetests'
        mock_call.return_value = 0
        
        test_plugin = Tests()
        test_plugin.app = MagicMock()
        test_plugin.app.pargs.single_test = None
        test_plugin.app.pargs.with_coverage = True
        
        test_plugin.default()
        
        mock_call.assert_called()
        args, kwargs = mock_call.call_args
        self.assertIn('--with-coverage', args[0])
        mock_exit.assert_called_with(0)

    @patch('dscan.plugins.tests.call')
    @patch('dscan.plugins.tests.which')
    @patch('dscan.plugins.tests.recursive_grep')
    @patch('sys.exit')
    def test_default_single_test(self, mock_exit, mock_grep, mock_which, mock_call):
        mock_which.return_value = '/usr/bin/nosetests'
        mock_call.return_value = 0
        mock_grep.return_value = 'some_tests.py'
        
        test_plugin = Tests()
        test_plugin.app = MagicMock()
        test_plugin.app.pargs.single_test = 'test_something'
        test_plugin.app.pargs.with_coverage = False
        
        test_plugin.default()
        
        mock_call.assert_called()
        args, kwargs = mock_call.call_args
        # Expected test path: dscan.tests.some_tests:SomeTests.test_something
        self.assertIn('dscan.tests.some_tests:SomeTests.test_something', args[0])
        mock_exit.assert_called_with(0)

    @patch('sys.exit')
    def test_conflicting_args(self, mock_exit):
        test_plugin = Tests()
        test_plugin.app = MagicMock()
        test_plugin.app.pargs.single_test = 'test'
        test_plugin.app.pargs.with_coverage = True
        
        # error() is usually implemented in HumanBasePlugin to print and exit
        # We mock it to just check if called and ensure it stops execution
        test_plugin.error = MagicMock(side_effect=SystemExit)
        
        with self.assertRaises(SystemExit):
            test_plugin.default()
        
        test_plugin.error.assert_called()
