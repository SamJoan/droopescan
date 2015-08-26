from twisted.trial.unittest import TestCase
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from dscan.plugins.internal.async_scan import _identify_url_file
from mock import patch
from dscan import tests
import dscan
import os

ASYNC_MODULE = 'dscan.plugins.internal.async_scan.'

class AsyncTests(TestCase):
    timeout = 3
    prev_cwd = None

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

