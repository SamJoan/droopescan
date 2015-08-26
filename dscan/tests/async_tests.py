from twisted.trial.unittest import TestCase
from twisted.internet import reactor
from twisted.internet.defer import Deferred, succeed, fail
from dscan.plugins.internal.async_scan import _identify_url_file, identify_lines, \
    identify_line
from mock import patch
from dscan import tests
import dscan
import os

ASYNC_MODULE = 'dscan.plugins.internal.async_scan.'
def f():
    """
    Returns a failed deferrer.
    """
    return fail(Exception('Failed'))

def s():
    """
    Returns a successful deferrer.
    """
    return succeed('')

class AsyncTests(TestCase):
    timeout = 3
    prev_cwd = None

    lines = ['http://adhwuiaihduhaknbacnckajcwnncwkakncw.com/\n',
            'http://adhwuiaihduhaknbacnckajcwnncwkakncx.com/\n',
            'http://adhwuiaihduhaknbacnckajcwnncwkakncy.com/\n']

    def setUp(self):
        self.prev_cwd = os.getcwd()
        # http://comments.gmane.org/gmane.comp.python.twisted/18676
        os.chdir(os.path.dirname(dscan.PWD[:-1]))

    def tearDown(self):
        os.chdir(self.prev_cwd)

    def test_lines_get_read(self):
        d = Deferred()
        def side_effect(lines):
            if len(lines) == 3:
                d.callback(lines)
            else:
                d.errback(lines)

            return d

        with patch(ASYNC_MODULE + 'identify_lines', side_effect=side_effect) as il:
            _identify_url_file(tests.VALID_FILE)

        return d

    @patch(ASYNC_MODULE + "identify_line")
    def test_calls_identify_line(self, il):
        dl = identify_lines(self.lines)
        calls = il.call_args_list
        assert len(calls) == len(self.lines)
        for i, comb_args in enumerate(calls):
            args, kwargs = comb_args
            assert args[0] == self.lines[i]

    @patch(ASYNC_MODULE + "error_line")
    def test_calls_identify_line_errback(self, el):
        ret = [f(), f(), s()]
        with patch(ASYNC_MODULE + "identify_line", side_effect=ret) as il:
            dl = identify_lines(self.lines)
            calls = el.call_args_list
            assert len(calls) == len(self.lines) - 1
            for i, comb_args in enumerate(calls):
                args, kwargs = comb_args
                assert args[0] == self.lines[i]

