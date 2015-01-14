from cement.utils import test
from common.testutils import decallmethods
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
from requests.exceptions import ConnectionError
from tests import BaseTest
import json
import re
import responses
import sys

class Capture(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self
    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        sys.stdout = self._stdout

@decallmethods(responses.activate)
class IntegrationTests(BaseTest):
    '''
        End-to-end tests for droopescan. These should not make any external
        requests.
    '''

    def setUp(self):
        super(IntegrationTests, self).setUp()

    def _mock_output_pl(self, line):
        """
            Parse a single line of output.
            @param line
            @return (verb, url, status_code) URL must have whatever replaced
                with self.base_url. status_code must be integer because
                otherwise weird errors will ensue due to fuzzy comparisons
                between strings and integers.
        """
        splat = line.split(' ')

        verb = splat[0][1:-1]
        status_code = splat[2].strip()

        url_removed_body = '/'.join(splat[1][:-3].split('/')[3:])
        url = self.base_url + url_removed_body

        return verb, url, int(status_code)

    def _unhandled_cb(self, request):
        print("Unhandled request to '%s' (%s)." % (request.url, request.method))
        return (404, {}, '')

    def mock_output(self, source):
        with open(source, 'r') as f:
            for line in f:
                verb, url, status_code = self._mock_output_pl(line)
                responses.add(verb.upper(), url, status=status_code)

        default_response = re.compile('.')
        responses.add_callback(responses.GET, default_response, callback=self._unhandled_cb)
        responses.add_callback(responses.HEAD, default_response, callback=self._unhandled_cb)

    def test_integration_drupal(self):
        self.mock_output("tests/resources/output_drupal.txt")

        self.add_argv(['scan', 'drupal', '-u', self.base_url, '-n', '100', '-o',
            'json'])

        with Capture() as out:
            self.app.run()

        json_raw = out[0]
        try:
            j = json.loads(json_raw)
        except:
            print(json_raw)
            raise

        assert len(j['interesting urls']['finds']) == 2
        assert len(j['plugins']['finds']) == 18
        assert len(j['themes']['finds']) == 0

