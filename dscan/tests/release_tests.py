from cement.utils import test
from common.testutils import decallmethods
from mock import patch, MagicMock, mock_open, Mock, create_autospec
from tests import BaseTest
import responses
import common.release_api as ra
import plugins.release

@decallmethods(responses.activate)
class ReleaseTests(BaseTest):

    release = None
    patchers = []

    def setUp(self):
        super(ReleaseTests, self).setUp()
        self._init_scanner()
        self.add_argv(['release'])
        self.release = plugins.release.Release()

    def tearDown(self):
        for patcher in self.patchers:
            patcher.stop()

    def p(self, *args, **kwargs):
        patcher = patch(spec=True, *args, **kwargs)
        self.patchers.append(patcher)

        return patcher.start()

    def mock_tests(self, raise_external=False, raise_human=False):
        internal = self.p('common.release_api.test_internal')
        external = self.p('common.release_api.test_external')
        human = self.p('common.release_api.test_human')

        if raise_external:
            external.side_effect = RuntimeError

        if raise_human:
            human.side_effect = RuntimeError

        return internal, external, human

    def test_tests_called(self):
        internal, external, _ = self.mock_tests(raise_external=True)
        raised = False
        try:
            self.app.run()
        except RuntimeError:
            raised = True

        assert internal.called
        assert external.called
        assert raised

    def test_skips_external(self):
        self.add_argv(['--skip-external'])
        internal, external, _ = self.mock_tests(raise_human=True)

        raised = False
        try:
            self.app.run()
        except RuntimeError:
            raised = True

        assert not external.called
        assert raised

    @test.raises(RuntimeError)
    def test_internal_raises(self):
        with patch('subprocess.call', return_value=1) as c:
            ra.test_internal()

    @test.raises(RuntimeError)
    def test_external_raises(self):
        with patch('subprocess.call', return_value=1) as c:
            ra.test_external()

    @test.raises(RuntimeError)
    def test_pypirc(self):
        with patch('os.path.isfile', return_value=False) as isfile:
            self.app.run()

