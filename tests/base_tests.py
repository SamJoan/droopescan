
from cement.utils import test
from common import file_len, ProgressBar, JsonOutput, StandardOutput
from common.testutils import decallmethods, MockBuffer
from mock import patch, MagicMock
from plugins.drupal import Drupal
from requests.exceptions import ConnectionError
from requests import Session
from tests import BaseTest
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

    @test.raises(IOError)
    def test_fails_io_when_url_file(self):
        self.add_argv(['scan', 'drupal'])
        self.add_argv(['--url-file', '/tmp/NONEXISTANTFILE'])
        self.app.run()

    @test.raises(RuntimeError)
    def test_errors_when_invalid_url(self):
        self.add_argv(['scan', 'drupal'])
        self.add_argv(self.param_plugins)
        self.add_argv(['--url', 'invalidurl'])
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
            'verb': 'a',
            'enumerate': 'p',
            'timeout': 15
        }
        opts_t = dict(opts_p)
        opts_t['enumerate'] = 't'

        drupal = Drupal()
        kwargs_p = drupal._functionality(opts_p)['plugins']['kwargs']
        kwargs_t = drupal._functionality(opts_t)['themes']['kwargs']

        # these should not be equal
        assert not kwargs_p == kwargs_t

    def test_user_agent(self):
        user_agent = "user_agent_string"
        self.scanner._general_init(user_agent=user_agent)

        assert self.scanner.session.headers['User-Agent'] == user_agent

    def test_no_verify(self):
        self.scanner._general_init()

        assert self.scanner.session.verify == False

    def test_progressbar(self):
        u = MockBuffer()
        p = ProgressBar(u)
        p.set(10, 100)

        a = u.get()[-4:]

        assert a == '10%)'
        assert " ===== " in u.get()

    def test_can_choose_output(self):
        output = JsonOutput()
        self.scanner._general_init(output=output)

        assert isinstance(self.scanner.out, JsonOutput)

    def test_can_choose_output_argv(self):
        self.add_argv(['scan', 'drupal'])
        self.add_argv(self.param_plugins)
        self.add_argv(['--output', 'json'])

        m = self.mock_controller('drupal', '_general_init')

        try:
            self.app.run()
        except:
            pass

        args, kwargs = m.call_args
        assert isinstance(kwargs['output'], JsonOutput)

    def test_output_defaults(self):
        jo = JsonOutput()
        so = StandardOutput()

        assert jo.errors_display == False
        assert so.errors_display == True

    @patch('__builtin__.print')
    def test_no_output_when_error_display_false(self, mock_print):
        jo = JsonOutput()
        jo.warn("""Things have not gone according to plan. Please exit the
                building in an orderly fashion.""")

        assert mock_print.called == False

    @patch('__builtin__.open')
    @patch('__builtin__.print')
    def test_log_output_when_error_display_false(self, mock_print, mock_open):
        jo = JsonOutput(error_log='/tmp/a')
        jo.warn("""Things have not gone according to plan. Please exit the
                building in an orderly fashion.""")

        assert mock_print.called == True
        assert mock_open.called == True

        args, kwargs = mock_print.call_args
        assert isinstance(kwargs['file'], MagicMock)
