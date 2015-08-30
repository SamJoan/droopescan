from dscan.common.async import request_url, REQUEST_DEFAULTS
from dscan.plugins.internal.async_scan import _identify_url_file, identify_lines, \
    identify_line, identify_url, identify_rfu, identify_version_url, \
    version_download, version_hash, version_get
from dscan.common.exceptions import UnknownCMSException
from dscan import tests
from dscan.plugins.drupal import Drupal
from dscan.plugins.silverstripe import Silverstripe
from mock import patch
from twisted.internet.defer import Deferred, succeed, fail
from twisted.internet import reactor
from twisted.internet import ssl
from twisted.trial.unittest import TestCase
from twisted.web.error import PageRedirect, Error
from twisted.web import client
import base64
import dscan
import dscan.common.plugins_util as pu
import dscan.common.async as async
import os


ASYNC = 'dscan.common.async.'
ASYNC_SCAN = 'dscan.plugins.internal.async_scan.'

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

    base_url = 'http://wiojqiowdjqoiwdjoqiwjdoqiwjfoqiwjfqowijf.com/'

    lines = ['http://adhwuiaihduhaknbacnckajcwnncwkakncw.com/\n',
            'http://adhwuiaihduhaknbacnckajcwnncwkakncx.com/\n',
            'http://adhwuiaihduhaknbacnckajcwnncwkakncy.com/\n']

    def setUp(self):
        self.prev_cwd = os.getcwd()
        # http://comments.gmane.org/gmane.comp.python.twisted/18676
        os.chdir(os.path.dirname(dscan.PWD[:-1]))

    def tearDown(self):
        os.chdir(self.prev_cwd)

    def mock_all_identify(self, ru_side=None):

        if ru_side:
            ru_kwargs = {'side_effect': ru_side}
        else:
            ru_kwargs = {}

        to_patch = [
            (ASYNC_SCAN + 'identify_url', {'return_value': ('', '')}),
            (ASYNC_SCAN + 'identify_version_url', {}),
            (ASYNC + 'request_url', ru_kwargs),
        ]

        for mock_method, kwargs in to_patch:
            patcher = patch(mock_method, autospec=True, **kwargs)
            if 'request_url' in mock_method:
                ru = patcher.start()
            elif 'identify_url' in mock_method:
                iu = patcher.start()
            else:
                patcher.start()

            self.addCleanup(patcher.stop)

        return ru, iu

    def test_lines_get_read(self):
        d = Deferred()
        def side_effect(lines):
            if len(lines) == 3:
                d.callback(lines)
            else:
                d.errback(lines)

            return d

        with patch(ASYNC_SCAN + 'identify_lines', side_effect=side_effect) as il:
            _identify_url_file(open(tests.VALID_FILE))

        return d

    @patch(ASYNC_SCAN + 'identify_line', autospec=True)
    def test_calls_identify_line(self, il):
        dl = identify_lines(self.lines)
        calls = il.call_args_list
        self.assertEquals(len(calls), len(self.lines))
        for i, comb_args in enumerate(calls):
            args, kwargs = comb_args
            self.assertEquals(args[0], self.lines[i])

    @patch(ASYNC_SCAN + 'error_line', autospec=True)
    def test_calls_identify_line_errback(self, el):
        ret = [f(), f(), s()]
        with patch(ASYNC_SCAN + 'identify_line', side_effect=ret) as il:
            dl = identify_lines(self.lines)
            calls = el.call_args_list
            self.assertEquals(len(calls), len(self.lines) - 1)
            for i, comb_args in enumerate(calls):
                args, kwargs = comb_args
                self.assertEquals(args[0],self.lines[i])

    def test_identify_strips_url(self):
        ru, iu = self.mock_all_identify()
        stripped = self.lines[0].strip()
        identify_line(self.lines[0])

        args, kwargs = ru.call_args
        self.assertEquals(ru.call_count, 1)
        self.assertEquals(args[0], stripped)

    def test_identify_accepts_space_separated_hosts(self):
        ru, iu = self.mock_all_identify()
        file_ip = open(tests.VALID_FILE_IP)
        for i, line in enumerate(file_ip):
            if i < 2:
                expected_url, expected_host = ('http://192.168.1.1/',
                        'example.com')
            elif i == 2:
                expected_url, expected_host = ('http://192.168.1.2/drupal/',
                        'example.com')

            identify_line(line)

            args, kwargs = ru.call_args_list[-1]
            self.assertEquals(args[0], expected_url)
            self.assertEquals(args[1], expected_host)

    @patch(ASYNC + 'reactor', autospec=True)
    def test_request_url_http(self, r):
        url = 'http://google.com/'
        host = None

        request_url(url, host)
        ct = r.connectTCP

        self.assertEquals(ct.call_count, 1)
        args, kwargs = ct.call_args
        self.assertEquals(args[0], 'google.com')
        self.assertEquals(args[1], 80)
        self.assertTrue(isinstance(args[2], client.HTTPClientFactory))

    @patch(ASYNC + 'reactor', autospec=True)
    def test_request_url_ssl(self, r):
        url = 'https://google.com/'
        host = None

        request_url(url, host)
        cs = r.connectSSL

        self.assertEquals(cs.call_count, 1)
        args, kwargs = cs.call_args
        self.assertEquals(args[0], 'google.com')
        self.assertEquals(args[1], 443)
        self.assertTrue(isinstance(args[2], client.HTTPClientFactory))
        self.assertTrue(isinstance(args[3], ssl.ClientContextFactory))


    @patch(ASYNC + 'client.HTTPClientFactory')
    @patch(ASYNC + 'reactor', autospec=True)
    def test_request_host_header(self, r, hcf):
        url = 'http://203.97.26.37/'
        host = 'google.com'
        url_with_host = 'http://google.com/'

        request_url(url, host)
        request_url(url_with_host, None)

        ct = r.connectTCP.call_args_list

        self.assertEquals(hcf.call_count, 2)
        args, kwargs = hcf.call_args_list[0]
        self.assertEquals(args[0], url)
        self.assertEquals(kwargs['headers']['Host'], host)
        self.assertEquals(ct[0][0][0], '203.97.26.37')

        args, kwargs = hcf.call_args_list[1]
        self.assertEquals(args[0], url_with_host)
        self.assertEquals(kwargs['headers']['Host'], host)
        self.assertEquals(ct[1][0][0], 'google.com')

    @patch(ASYNC + 'client.HTTPClientFactory')
    @patch(ASYNC + 'reactor', autospec=True)
    def test_request_defaults(self, r, hcf):
        url = 'http://google.com/'
        host = None
        defaults = REQUEST_DEFAULTS

        request_url(url, host)

        self.assertEquals(hcf.call_count, 1)
        args, kwargs = hcf.call_args

        for key in defaults:
            self.assertEquals(kwargs[key], defaults[key])

    def test_request_redirect_follow(self):
        redirect_url = 'http://urlb.com/'
        r = PageRedirect('redirect')
        r.location = redirect_url
        ru, iu = self.mock_all_identify(ru_side=r)

        identify_line(self.lines[0])

        self.assertEquals(iu.call_count, 1)
        args, kwargs = iu.call_args

        self.assertEquals(args[0], redirect_url)

    def test_request_redirect_follow_query_string(self):
        redirect_url = 'http://urlb.com/?aa=a'
        r = PageRedirect('redirect')
        r.location = redirect_url

        ru, iu = self.mock_all_identify(ru_side=r)

        identify_line(self.lines[0])
        args, kwargs = iu.call_args
        self.assertEquals(args[0], 'http://urlb.com/')

    def test_identify_calls_all_rfu(self):
        rfu = pu.get_rfu()
        with patch(ASYNC + 'download_url', autospec=True) as du:
            identify_url(self.base_url, None)

            self.assertEquals(du.call_count, len(rfu))
            for i, call in enumerate(du.call_args_list):
                args, kwargs = call
                self.assertEquals(args[0], self.base_url + rfu[i])
                self.assertTrue(args[2].endswith(async.filename_encode(rfu[i])))

    def test_identify_calls_identify_rfu(self):
        tempdir = '/tmp/dscan18293u1/'
        with patch(ASYNC_SCAN + 'download_rfu', return_value=tempdir, autospec=True) as dr:
            with patch(ASYNC_SCAN + 'identify_rfu') as ir:
                identify_url(self.base_url, None)

                args, kwargs = ir.call_args

                self.assertEqual(ir.call_count, 1)
                self.assertEqual(args[0], tempdir)

    @patch('os.path.isdir', return_value=True)
    @patch('dscan.plugins.internal.async_scan.mkdtemp')
    @patch('shutil.rmtree')
    def test_identify_raises_when_none_found(self, rt, mt, isdir):
        ret = '/tmp/lelelellee'
        mt.return_value = ret

        def fail(*args, **kwargs):
            return f()

        rfu = pu.get_rfu()
        with patch(ASYNC + 'download_url', side_effect=fail, autospec=True) as du:
            with patch(ASYNC_SCAN + 'identify_rfu') as ir:
                self.assertFailure(identify_url(self.base_url, None),
                        UnknownCMSException)
                self.assertEquals(ir.call_count, 0)

                args, kwargs = rt.call_args
                self.assertEquals(rt.call_count, 1)
                self.assertEquals(mt.call_count, 1)
                self.assertEquals(args[0], ret + "/")


    def test_identify_rfu_single_file(self):
        rfu = pu.get_rfu()
        fake_dir = '/tmp/dsadasdadaa/'
        joomla_file = fake_dir + async.filename_encode("media/system/js/validate.js")
        def isfile(path):
            if path == joomla_file:
                return True
            else:
                return False

        with patch("os.path.isfile", side_effect=isfile, autospec=True) as if_mock:
            d = identify_rfu(fake_dir)
            cms_name = self.successResultOf(d)

            self.assertEquals(cms_name, "joomla")
            self.assertEquals(if_mock.call_count, len(rfu))

    def test_identify_rfu_all_found(self):
        fake_dir = '/tmp/dsadasdadaa/'
        def isfile(path):
            return True

        with patch("os.path.isfile", side_effect=isfile, autospec=True) as if_mock:
            d = identify_rfu(fake_dir)
            self.assertFailure(d, UnknownCMSException)

    @patch('shutil.rmtree')
    def test_identify_url_cleans_on_failure(self, rt):
        tempdir = '/tmp/dscan18293u1/'
        with patch('os.path.isdir', return_value=True, autospec=True) as isdir:
            with patch(ASYNC_SCAN + 'download_rfu', return_value=tempdir, autospec=True) as dr:
                with patch(ASYNC_SCAN + 'identify_rfu', side_effect=RuntimeError()) as ir:
                    self.assertFailure(identify_url('http://google.com/', None),
                            RuntimeError)

                    args, kwargs = rt.call_args
                    self.assertEquals(rt.call_count, 1)
                    self.assertEquals(isdir.call_count, 1)
                    self.assertEquals(args[0], tempdir)

    @patch(ASYNC_SCAN + 'version_hash', autospec=True)
    @patch(ASYNC_SCAN + 'version_download', autospec=True)
    def test_version_calls_download(self, dl, vh):
        identify_version_url('http://google.com', None, 'silverstripe',
                '/tmp/aadada/')

        self.assertTrue(dl.called)

    @patch('dscan.common.plugins_util.VersionsFile.__init__', return_value=None, autospec=True)
    @patch('os.path.isfile', autospec=True)
    @patch('dscan.common.plugins_util.VersionsFile.files_get_all', autospec=True)
    def test_version_download(self, fga, isfile, vf_init):
        already_gotten = 'fefefefefe.txt'
        files = [already_gotten, 'aaaa', 'bbb', 'cacacascscsc']
        tempdir = "/tmp/dwjdiwjdwwww/"
        base_url = 'http://google.com/'
        def isfile_cb(path):
            if path == tempdir + async.filename_encode(already_gotten):
                return True

            return False

        fga.return_value = files
        isfile.side_effect = isfile_cb
        with patch(ASYNC + 'download_url', autospec=True) as du:
            version_download(base_url, None, Drupal, tempdir)

            self.assertEquals(du.call_count, len(files) - 1)
            for i, call in enumerate(du.call_args_list):
                args, kwargs = call
                self.assertEquals(args[0], base_url + files[i + 1])
                self.assertEquals(args[2], tempdir + async.filename_encode(files[i + 1]))

    @patch('dscan.common.plugins_util.VersionsFile.files_get_all', autospec=True)
    @patch('dscan.common.async.subprocess', autospec=True)
    def test_version_identify(self, s, fga):
        tempdir = '/tmp/adhadada/'
        files = ['aaa', 'aaaa', 'bbb', 'cacacascscsc']
        fga.return_value = files

        version_hash(Drupal, tempdir)

        self.assertEquals(s.call_count, 1)
        for i, call in enumerate(s.call_args_list):
            args, kwargs = call
            for i, file_to_hash in enumerate(args[1]):
                self.assertEquals(file_to_hash, tempdir + async.filename_encode(files[i]))

    def test_version_get_from_stdout(self):
        stdout = """33e888d268d7b416e8aa67ea6f0a23cf /tmp/dscan5Z0k3K/636D732F6A6176617363726970742F434D534D61696E2E547265652E6A73
964a5d044ba95792b49456f8b266bbab /tmp/dscan5Z0k3K/6672616D65776F726B2F6A6176617363726970742F48746D6C456469746F724669656C642E6A73
7f5bf250469639de306f3bca2ed03666 /tmp/dscan5Z0k3K/6672616D65776F726B2F6373732F417373657455706C6F61644669656C642E637373
5735ae836a12809611fb4a0f010920ea /tmp/dscan5Z0k3K/6672616D65776F726B2F6373732F55706C6F61644669656C642E637373
"""

        out = version_get(Silverstripe, stdout)
        self.assertEquals(out, ['3.1.7', '3.1.7-rc1', '3.1.8', '3.1.9', '3.1.9-rc1'])

