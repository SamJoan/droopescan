import unittest
from mock import patch, MagicMock
from dscan.droopescan import reorder_argv_for_backward_compatibility, handle_interrupt, DroopeScanBase
from dscan import common
import sys

class DroopescanTests(unittest.TestCase):
    
    def test_reorder_argv_too_short(self):
        self.assertEqual(reorder_argv_for_backward_compatibility(['prog']), ['prog'])
        self.assertEqual(reorder_argv_for_backward_compatibility(['prog', 'scan']), ['prog', 'scan'])

    def test_reorder_argv_no_scan(self):
        argv = ['prog', 'other', 'cmd']
        self.assertEqual(reorder_argv_for_backward_compatibility(argv), argv)

    def test_reorder_argv_scan_last(self):
        argv = ['prog', 'scan']
        self.assertEqual(reorder_argv_for_backward_compatibility(argv), argv)

    def test_reorder_argv_old_format(self):
        # scan cms -u URL
        argv = ['prog', 'scan', 'drupal', '-u', 'http://example.com']
        expected = ['prog', 'scan', '-u', 'http://example.com', 'drupal']
        self.assertEqual(reorder_argv_for_backward_compatibility(argv), expected)

    def test_reorder_argv_new_format(self):
        # scan -u URL drupal (already correct)
        argv = ['prog', 'scan', '-u', 'http://example.com', 'drupal']
        self.assertEqual(reorder_argv_for_backward_compatibility(argv), argv)

    def test_reorder_argv_default_subcommand(self):
        # scan -u URL (missing cms, implies default)
        argv = ['prog', 'scan', '-u', 'http://example.com']
        expected = ['prog', 'scan', '-u', 'http://example.com', 'default']
        self.assertEqual(reorder_argv_for_backward_compatibility(argv), expected)

    def test_handle_interrupt(self):
        common.shutdown = False
        handle_interrupt(None, None)
        self.assertTrue(common.shutdown)
        common.shutdown = False # reset

    @patch('dscan.droopescan.version_get')
    def test_base_controller_default(self, mock_version_get):
        mock_version_get.return_value = '1.0.0'
        base = DroopeScanBase()
        with patch('sys.stdout') as mock_stdout:
            # We need to capture print output. 
            # Since DroopeScanBase.default uses print(), we can mock print or sys.stdout
            
            # Since print writes to sys.stdout by default...
            # But in python 2 print is a statement. 
            # The file has from __future__ import print_function, so it's a function.
            
            with patch('builtins.print') as mock_print:
                base.default()
                mock_print.assert_called()
                args, _ = mock_print.call_args
                self.assertIn('1.0.0', args[0])

