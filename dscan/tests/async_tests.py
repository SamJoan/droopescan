from twisted.trial.unittest import TestCase
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from dscan.plugins.internal.async_scan import _identify_url_file
from mock import patch
from dscan import tests
import os

# http://comments.gmane.org/gmane.comp.python.twisted/18676
os.chdir(dscan.PWD)

ASYNC_MODULE = 'dscan.plugins.internal.async_scan.'

class AsyncTests(TestCase):
    timeout = 3
    def test_lines_get_read(self):
        with patch(ASYNC_MODULE + 'identify_lines') as il:
            _identify_url_file(tests.VALID_FILE)

            args, kwargs = il.call_args()
            print(args, kwargs)


