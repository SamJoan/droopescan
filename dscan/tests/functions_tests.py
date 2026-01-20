import unittest
from mock import patch, MagicMock, mock_open
from dscan.common import functions
from io import BytesIO

class FunctionsTests(unittest.TestCase):
    
    def test_repair_url(self):
        self.assertEqual(functions.repair_url("example.com"), "http://example.com/")
        self.assertEqual(functions.repair_url("http://example.com"), "http://example.com/")
        self.assertEqual(functions.repair_url("http://example.com/"), "http://example.com/")
        self.assertEqual(functions.repair_url("http://example.com?q=1"), "http://example.com/")
        self.assertEqual(functions.repair_url("example.com\n"), "http://example.com/")

    def test_base_url(self):
        self.assertEqual(functions.base_url("http://example.com/foo/bar"), "http://example.com/")
        self.assertEqual(functions.base_url("https://example.com/foo"), "https://example.com/")
        self.assertFalse(functions.base_url("example.com/foo"))

    def test_strip_whitespace(self):
        self.assertEqual(functions.strip_whitespace("  foo   bar  "), " foo bar ")

    def test_file_len(self):
        m = mock_open(read_data="line1\nline2\n")
        with patch('dscan.common.functions.open', m, create=True):
            self.assertEqual(functions.file_len("test"), 2)

    def test_version_gt(self):
        # Basic
        self.assertTrue(functions.version_gt("1.1", "1.0"))
        self.assertFalse(functions.version_gt("1.0", "1.1"))
        self.assertFalse(functions.version_gt("1.0", "1.0"))
        
        # Length mismatch
        self.assertTrue(functions.version_gt("1.0.1", "1.0"))
        self.assertFalse(functions.version_gt("1.0", "1.0.1"))
        
        # RC
        self.assertTrue(functions.version_gt("1.0", "1.0-rc1"))
        self.assertFalse(functions.version_gt("1.0-rc1", "1.0"))
        self.assertTrue(functions.version_gt("1.0-rc2", "1.0-rc1"))
        
        # With letters
        self.assertTrue(functions.version_gt("1.a.1", "1.a.0")) # letters stripped 1.1 vs 1.0
        
        # Complex
        self.assertTrue(functions.version_gt("8.0-alpha12", "8.0-alpha6"))

    def test_exc_handle(self):
        out = MagicMock()
        try:
            raise ValueError("Test error")
        except:
            # Test with testing=True (full traceback)
            with patch('dscan.common.functions.print') as mock_print:
                functions.exc_handle("http://url", out, True)
                out.warn.assert_called()
                mock_print.assert_called()
            
            # Test with testing=False (should still warn for ValueError)
            out.reset_mock()
            functions.exc_handle("http://url", out, False)
            out.warn.assert_called()

    def test_tail(self):
        content = b"1\n2\n3\n4\n5\n"
        f = BytesIO(content)
        lines = functions.tail(f, 2)
        self.assertEqual(lines, ["4", "5"])
        
        f.seek(0)
        lines = functions.tail(f, 10)
        self.assertEqual(lines, ["1", "2", "3", "4", "5"])

    def test_process_host_line(self):
        self.assertEqual(functions.process_host_line("url"), ("url", None))
        self.assertEqual(functions.process_host_line("url host"), ("url", "host"))
        self.assertEqual(functions.process_host_line("url\thost"), ("url", "host"))
        self.assertEqual(functions.process_host_line(None), (None, None))

    def test_result_anything_found(self):
        res = {'version': {'is_empty': True}}
        self.assertFalse(functions.result_anything_found(res))
        
        res = {'version': {'is_empty': False}}
        self.assertTrue(functions.result_anything_found(res))
        
        res = {'other': {'is_empty': False}}
        self.assertFalse(functions.result_anything_found(res))

