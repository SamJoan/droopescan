from cement.utils import test
from common.testutils import file_len, decallmethods
from requests.exceptions import ConnectionError
from tests import BaseTest
import responses

@decallmethods(responses.activate)
class BaseTests(BaseTest):
    """
        Basic tests, and generic tests.
    """
    @test.raises(RuntimeError)
    def test_errors_when_no_module(self):
        self.app.run()

    @test.raises(RuntimeError)
    def test_errors_when_no_url(self):
        self.add_argv(["drupal"])
        self.app.run()

    @test.raises(RuntimeError)
    def test_errors_when_invalid_url(self):
        self.add_argv(["drupal"])
        self.add_argv(["--url", "invalidurl"])
        self.app.run()

    @test.raises(RuntimeError)
    def test_errors_when_invalid_enumerate(self):
        self.add_argv(["drupal"])
        self.add_argv(self.param_base + ["-e", 'z'])
        self.app.run()

    @test.raises(RuntimeError)
    def test_errors_when_invalid_method(self):
        self.add_argv(["drupal"])
        self.add_argv(self.param_plugins + ["--method", "derpo"])
        self.app.run()

    @test.raises(ConnectionError)
    def test_calls_plugin(self):
        self.add_argv(["drupal"])
        self.add_argv(self.param_plugins)
        self.add_argv(["--method", "forbidden"])

        self.app.run()

    @test.raises(ConnectionError)
    def test_calls_theme(self):
        self.add_argv(["drupal"])
        self.add_argv(self.param_themes)

        self.add_argv(["--method", "forbidden"])

        self.app.run()

    def test_calls_all(self):
        self.add_argv(["drupal"])
        self.add_argv(self.param_all)
        self.add_argv(["--method", "forbidden"])

        all_mocks = self.mock_all_enumerate('drupal')

        self.app.run()

        for m in all_mocks:
            assert m .called, "module %s" % m

    def test_doesnt_crash_on_runtimeerror(self):
        self.add_argv(["drupal"])
        self.add_argv(self.param_all)
        self.add_argv(["--method", "forbidden"])

        all_mocks = self.mock_all_enumerate('drupal', side_effect_on_one=True)

        self.app.run()




