from cement.utils import test
from dscan.common.testutils import decallmethods
from dscan import plugins
from dscan.tests import BaseTest
from mock import patch, MagicMock, mock_open, Mock, create_autospec
import dscan.common.release_api as ra
import dscan.plugins.release
import responses
import sys

@decallmethods(responses.activate)
class ReleaseTests(BaseTest):

    release = None

    def setUp(self):
        super(ReleaseTests, self).setUp()
        self._init_scanner()
        self.add_argv(['release'])
        self.release = plugins.release.Release()

    def p(self, *args, **kwargs):
        patcher = patch(spec=True, *args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def mock_tests(self, raise_external=False, raise_human=False):
        check_pypirc = self.p('dscan.common.release_api.check_pypirc')
        internal = self.p('dscan.common.release_api.test_internal')
        external = self.p('dscan.common.release_api.test_external')
        human = self.p('dscan.common.release_api.test_human')

        if raise_external:
            external.side_effect = RuntimeError

        if raise_human:
            human.side_effect = RuntimeError

        return internal, external, human

    def mock_input(self, ret_val=None, side_eff=None):
        if sys.version_info < (3, 0, 0):
            builtin = "__builtin__"
            inp = "raw_input"
        else:
            builtin = "builtins"
            inp = "input"

        inp = self.p("%s.%s" % (builtin, inp))

        if ret_val:
            inp.return_value = ret_val

        if side_eff:
            inp.side_effect = side_eff

        return (builtin, inp)

    def _mock_cm(self):
        mocks = []

        mocks.append(self.p("dscan.common.release_api.read_first_line"))
        mocks.append(self.p("dscan.common.release_api.get_input"))
        mocks.append(self.p("dscan.common.release_api.changelog"))
        mocks.append(self.p("dscan.common.release_api.confirm", return_value=True))
        mocks.append(self.p("dscan.common.release_api.prepend_to_file"))

        return mocks

    def test_tests_called(self):
        internal, external, _ = self.mock_tests(raise_external=True)
        raised = False
        try:
            self.app.run()
        except RuntimeError as e:
            print(e)
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

    def test_read_first_line(self):
        real_version = "1.33.7"

        with patch('dscan.common.release_api.open', create=True) as mock_open:
             mock_open.return_value = MagicMock()
             mock_open().__enter__().readline.return_value = "%s\n" % real_version
             version = ra.read_first_line('../WHATEVER')

             assert version == real_version

    def test_human(self):
        with patch('dscan.common.release_api.confirm') as mc:
            ra.test_human()

            assert mc.called

    @test.raises(RuntimeError)
    def test_human_raises(self):
        with patch('dscan.common.release_api.confirm', return_value=False) as mc:
            ra.test_human()

    def test_get_input(self):
        question = "Is this a question?"
        return_value = "Yes."

        builtin, ri = self.mock_input(return_value)
        with patch("%s.print" % builtin) as p:
                response = ra.get_input(question)

                assert p.called
                assert p.call_args[0][0] == question

                assert ri.called
                assert response == return_value

    def test_changelog(self):
        version = "1.33.7"
        changes = " Change stuff."
        with patch("tempfile.NamedTemporaryFile") as ntf:
            with patch('subprocess.call', return_value=0) as c:
                w = ntf().__enter__().write
                r = ntf().__enter__().read
                r.return_value = changes

                ret_val = ra.changelog(version)

                header = w.call_args[0][0]

                assert version in header
                assert ret_val == header + changes

    def test_confirm(self):
        side_eff = ["HA!", "y"]
        builtins, inp = self.mock_input(side_eff=side_eff)

        result = ra.confirm("")
        assert inp.call_count == 2
        assert result == True

    def test_confirm_false(self):
        side_eff = ["n"]
        builtins, inp = self.mock_input(side_eff=side_eff)

        result = ra.confirm("")
        assert result == False

    def test_prepend_to_file(self):
        f = "CHANGELOL"

        prev = "adadadad\n"
        new = "bsbbssbbs\n"

        with patch('dscan.common.release_api.open', create=True) as mo:
            mo().read.return_value = prev
            ra.prepend_to_file(f, new)

            w = mo().write
            first_write = w.call_args_list[0][0][0]
            second_write = w.call_args_list[1][0][0]

            assert w.call_count == 2
            assert first_write == new
            assert second_write == prev

    def test_changelog_modify(self):
        all_mocks = self._mock_cm()
        ra.changelog_modify()

        for mock in all_mocks:
            assert mock.called

