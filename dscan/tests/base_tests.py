from __future__ import unicode_literals
from cement.utils import test
from dscan.common.exceptions import FileEmptyException
from dscan.common import file_len, ProgressBar, JsonOutput, StandardOutput
from dscan.common.plugins_util import plugins_base_get
from dscan.common.testutils import decallmethods, MockBuffer
from dscan import common
from dscan.plugins.drupal import Drupal
from dscan.tests import BaseTest
from mock import patch, MagicMock, mock_open
from requests.exceptions import ConnectionError
from requests import Session
import io
import os
import responses
import sys

@decallmethods(responses.activate)
class BaseTests(BaseTest):
    '''
        Basic tests, and generic tests.
    '''

    def setUp(self):
        super(BaseTests, self).setUp()
        self._init_scanner()

    @test.raises(RuntimeError)
    def test_errors_when_no_url(self):
        self.add_argv(['scan', 'drupal'])
        self.app.run()

    @test.raises(RuntimeError)
    def test_errors_when_no_url_identify(self):
        self.add_argv(['scan', 'default'])
        self.app.run()

    @test.raises(IOError)
    def test_fails_io_when_url_file(self):
        self.add_argv(['scan', 'drupal'])
        self.add_argv(['--url-file', '/tmp/NONEXISTANTFILE'])
        self.app.run()

    @test.raises(SystemExit)
    def test_errors_when_invalid_enumerate(self):
        self.add_argv(['scan', 'drupal'])
        self.add_argv(self.param_base + ['-e', 'z'])
        self.app.run()

    @test.raises(SystemExit)
    def test_errors_when_invalid_method(self):
        self.add_argv(['scan', 'drupal'])
        self.add_argv(self.param_plugins + ['--method', 'derpo'])
        self.app.run()

    @test.raises(ConnectionError)
    def test_calls_plugin(self):
        self.add_argv(['scan', 'drupal'])
        self.add_argv(self.param_plugins)
        self.add_argv(['--method', 'forbidden'])

        self.app.run()

    @test.raises(ConnectionError)
    def test_calls_theme(self):
        self.add_argv(['scan', 'drupal'])
        self.add_argv(self.param_themes)
        self.add_argv(['--method', 'forbidden'])

        self.app.run()

    def test_calls_all(self):
        self.add_argv(['scan', 'drupal'])
        self.add_argv(self.param_all)
        self.add_argv(['--method', 'forbidden'])

        all_mocks = self.mock_all_enumerate('drupal')

        self.app.run()

        for m in all_mocks:
            assert m.called, 'module %s' % m

    def test_fix_dereference_bug(self):
        '''
            test for dereference that made the app fail even though
            all tests were passing.
        '''

        plugins_base_url = 'plugins_base_url'
        themes_base_url = 'themes_base_url'
        opts_p = {
            'url': self.base_url,
            'plugins_base_url': plugins_base_url,
            'themes_base_url': themes_base_url,
            'scanning_method': 'a',
            'number': 'a',
            'threads': 'a',
            'threads_enumerate': None,
            'threads_identify': None,
            'threads_scan': None,
            'verb': 'a',
            'enumerate': 'p',
            'timeout': 15,
            'headers': {},
            'no_fingerprint_fallback': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0'
        }
        opts_t = dict(opts_p)
        opts_t['enumerate'] = 't'

        drupal = Drupal()
        kwargs_p = drupal._functionality(opts_p)['plugins']['kwargs']
        kwargs_t = drupal._functionality(opts_t)['themes']['kwargs']

        # these should not be equal
        assert not kwargs_p == kwargs_t

    def test_user_agent(self):
        self.scanner._general_init(self.test_opts)

        assert self.scanner.session.headers['User-Agent'] == self.scanner.DEFAULT_UA

    def test_no_verify(self):
        self.scanner._general_init(self.test_opts)

        assert self.scanner.session.verify == False

    def test_can_choose_output(self):
        opts = self.test_opts
        opts['output'] = 'json'

        self.scanner._general_init(opts)

        assert isinstance(self.scanner.out, JsonOutput)

    def test_can_choose_output_argv(self):
        self.add_argv(['scan', 'drupal'])
        self.add_argv(self.param_plugins)
        self.add_argv(['--output', 'json'])

        with patch('dscan.plugins.internal.base_plugin_internal.JsonOutput') as jo:
            try:
                self.app.run()
            except:
                pass
            
            assert jo.called

    def test_output_defaults(self):
        jo = JsonOutput()
        so = StandardOutput()

        assert jo.errors_display == False
        assert so.errors_display == True

    def test_output_json_when_url_file(self):
        self.add_argv(['scan', 'drupal'])
        self.add_argv(['--url-file', self.valid_file])

        with patch('dscan.plugins.internal.base_plugin_internal.JsonOutput') as jo:
            try:
                self.app.run()
            except:
                pass
            
            assert jo.called

    def test_output_standard_when_normal_url(self):
        self.add_argv(['scan', 'drupal'])
        self.add_argv(['-u', self.base_url])

        with patch('dscan.plugins.internal.base_plugin_internal.StandardOutput') as so:
            try:
                self.app.run()
            except:
                pass
            
            assert so.called

    def test_no_output_when_error_display_false(self):
        with patch('sys.stdout', new=io.BytesIO()) as fake_out:
            jo = JsonOutput()
            jo.warn("""Things have not gone according to plan. Please exit the
                    building in an orderly fashion.""")

            val = fake_out.getvalue()

        assert val == b""

    def test_no_output_when_exception(self):
        self.app.testing = False
        self.add_argv(['scan', 'drupal'])
        self.add_argv(['-U', self.valid_file])
        self.add_argv(['--output', 'json'])
        self.add_argv(['--method', 'forbidden'])

        all_mocks = self.mock_all_enumerate('drupal')
        if sys.version_info < (3, 0, 0):
            mock_string_method = io.BytesIO
        else:
            mock_string_method = io.StringIO

        with patch('sys.stdout', new=mock_string_method()) as fake_out:
            self.app.run()
            val = fake_out.getvalue()

        # Expected output is one line of json followed by a newline.
        lines = val.split("\n")
        assert len(lines) == 2
        assert lines[0].startswith('{')
        assert lines[1] == ''

    def test_log_output_when_error_display_false(self):

        warn_string = 'warn_string'
        error_file = '/tmp/droopescan_test_error_log'

        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            jo = JsonOutput(error_log=error_file)
            jo.error_log = io.StringIO()
            jo.warn(warn_string)

            file_output = jo.error_log.getvalue()
            standard_out = fake_out.getvalue()

        assert standard_out == ""
        assert warn_string in file_output

    def test_debug_requests(self):
        self.add_argv(['scan', 'drupal'])
        self.add_argv(['--url', self.base_url])
        self.add_argv(['--debug-requests'])

        with patch('dscan.common.RequestsLogger._print') as rlp:
            try:
                self.app.run()
            except:
                pass

            assert rlp.called

    def test_not_debug_requests(self):
        self.add_argv(['scan', 'drupal'])
        self.add_argv(['--url', self.base_url])

        with patch('dscan.common.RequestsLogger._print') as rlp:
            try:
                self.app.run()
            except:
                pass

            assert not rlp.called

    def test_file_len_empty_file(self):
        m = mock_open()
        with patch('dscan.common.functions.open', m, create=True) as o:
            ln = file_len("test")
            print(o.call_args_list)
            assert ln == 0

    @patch.object(common.StandardOutput, 'warn')
    def test_kali_old_requests_bug(self, warn):
        drupal = Drupal()
        with patch('requests.adapters', spec_set=["force_attr_error"]):
            drupal._general_init(self.test_opts)

            assert warn.called

    def test_url_file_accepts_relative(self):
        self.add_argv(['scan', 'drupal'])
        self.add_argv(['--url-file', self.valid_file])

        m = mock_open()
        with patch('dscan.plugins.internal.base_plugin_internal.open', m, create=True) as o:
            url_scan = self.mock_controller('drupal', 'url_scan')
            self.app.run()

            assert os.getcwd() + "/" + self.valid_file == o.call_args_list[0][0][0]

    def test_url_file_leaves_full(self):
        full_path = "/" + self.valid_file
        self.add_argv(['scan', 'drupal'])
        self.add_argv(['--url-file', full_path])

        m = mock_open()
        with patch('dscan.plugins.internal.base_plugin_internal.open', m, create=True) as o:
            with patch('dscan.plugins.internal.base_plugin_internal.BasePluginInternal.check_file_empty', autospec=True):
                url_scan = self.mock_controller('drupal', 'url_scan')
                self.app.run()

                assert full_path == o.call_args_list[0][0][0]

    @test.raises(FileEmptyException)
    def test_url_file_empty(self):
        self.add_argv(['scan', 'drupal'])
        self.add_argv(['--url-file', self.empty_file])

        self.app.run()

    @test.raises(FileEmptyException)
    def test_url_file_empty_identify(self):
        self.add_argv(['scan'])
        self.add_argv(['--url-file', self.empty_file])

        self.app.run()

    def test_progressbar_simple(self):
        u = MockBuffer()
        p = ProgressBar(u, 100, 'test')

        for _ in range(10):
            p.increment_progress()

        a = u.get()[-4:]

        assert a == '10%)'
        assert " ===== " in u.get()

    def test_resume_scan(self):
        url_file = 'dscan/tests/resources/resume_url_file.txt'
        error_file = 'dscan/tests/resources/resume_error_single.txt'

        self.add_argv(['scan', 'drupal'])
        self.add_argv(['--url-file', url_file])
        self.add_argv(['--error-log', error_file])
        self.add_argv(['--resume'])
        mock_module = 'dscan.plugins.internal.base_plugin_internal.BasePluginInternal.url_scan'

        m = mock_open()
        with patch('dscan.common.output.open', m, create=True) as o:
            with patch(mock_module, autospec=True) as m:
                self.app.run()

                calls = m.call_args_list
                for i, call in enumerate(calls):
                    args, kwargs = call
                    url = args[1]
                    if i == 0:
                        assert url == 'example3.com\n'
                    elif i == 1:
                        assert url == 'example4.com\n'
                    else:
                        assert False, "Only two calls expected."


    def test_resume_identify(self):
        url_file = 'dscan/tests/resources/resume_url_file.txt'
        error_file = 'dscan/tests/resources/resume_error_single.txt'

        self.add_argv(['scan'])
        self.add_argv(['--url-file', url_file])
        self.add_argv(['--error-log', error_file])
        self.add_argv(['--resume'])
        mock_module = 'dscan.plugins.internal.scan.Scan._process_generate_futures'

        m = mock_open()
        with patch('dscan.common.output.open', m, create=True) as o:
            with patch(mock_module, autospec=True) as m:
                self.app.run()

                args, kwargs = m.call_args
                urls = args[1]
                assert urls[0] == "example3.com\n"
                assert urls[1] == "example4.com\n"

    def test_resume_single(self):
        url_file = 'dscan/tests/resources/resume_url_file.txt'
        error_file = 'dscan/tests/resources/resume_error_single.txt'
        result = self.scanner.resume(url_file, error_file)
        assert result == 2

    def test_resume_multi(self):
        url_file = 'dscan/tests/resources/resume_url_file.txt'
        error_file = 'dscan/tests/resources/resume_error_multi.txt'
        result = self.scanner.resume(url_file, error_file)
        assert result == 2

    def test_plugins_get(self):
        plugins = plugins_base_get()
        assert len(plugins) > 3

    def test_cookie_prefix_removal(self):
        self.add_argv(['scan', 'drupal', '-u', 'http://example.org', '--cookie', 'Cookie: SESS123=abc; other=def'])
        try:
            self.app.run()
        except:
            pass
        pargs = self.app.pargs
        
        opts = self.scanner._options(pargs)
        assert opts['cookie'] == 'SESS123=abc; other=def'

    def test_cookie_prefix_removal_case_insensitive(self):
        self.add_argv(['scan', 'drupal', '-u', 'http://example.org', '--cookie', 'cookie: SESS123=abc; other=def'])
        try:
            self.app.run()
        except:
            pass
        pargs = self.app.pargs
        
        opts = self.scanner._options(pargs)
        assert opts['cookie'] == 'SESS123=abc; other=def'

    def test_cookie_no_prefix_remains_unchanged(self):
        self.add_argv(['scan', 'drupal', '-u', 'http://example.org', '--cookie', 'SESS123=abc; other=def'])
        try:
            self.app.run()
        except:
            pass
        pargs = self.app.pargs
        
        opts = self.scanner._options(pargs)
        assert opts['cookie'] == 'SESS123=abc; other=def'

    def test_session_cookie_header_is_set(self):
        from mock import MagicMock
        pargs = MagicMock()
        pargs.cookie = 'Cookie: SESS123=abc'
        pargs.url_file = None
        pargs.url = 'http://example.org'
        pargs.enumerate = 'a'
        pargs.verb = 'head'
        pargs.method = None
        pargs.output = 'standard'
        pargs.timeout = 300
        pargs.timeout_host = 1800
        pargs.user_agent = 'Mozilla/5.0'
        pargs.hide_progressbar = False
        pargs.debug_requests = False
        pargs.follow_redirects = True
        pargs.plugins_base_url = None
        pargs.themes_base_url = None
        pargs.debug = False
        pargs.resume = False
        pargs.number = 10
        pargs.no_fingerprint_fallback = False
        pargs.error_log = None
        pargs.host = None
        pargs.threads = 4
        pargs.threads_identify = None
        pargs.threads_scan = None
        pargs.threads_enumerate = None
        pargs.massscan_override = False

        opts = self.scanner._options(pargs)
        self.scanner._general_init(opts)
        
        assert self.scanner.session.headers['Cookie'] == 'SESS123=abc'


