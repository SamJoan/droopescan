from cement.core import controller, foundation, backend
from cement.utils import test
from common.testutils import file_len, decallmethods
from droopescan import DroopeScan
from mock import patch, MagicMock
import responses

class BaseTest(test.CementTestCase):
    app_class = DroopeScan
    scanner = None

    base_url = "http://adhwuiaihduhaknbacnckajcwnncwkakncw.com/"

    param_base = ["--url", base_url, '-n', '10']
    param_plugins = param_base + ["-e", 'p']
    param_themes = param_base + ["-e", 't']
    param_all = param_base + ["-e", 'a']

    def setUp(self):
        super(BaseTest, self).setUp()
        self.reset_backend()
        self.app = DroopeScan(argv=[],
            plugin_config_dir="./plugins.d",
            plugin_dir="./plugins")
        self.app.testing = True
        self.app.setup()

    def tearDown(self):
        self.app.close()

    def mock_controller(self, plugin_label, method, return_value = None, side_effect = None):
        """
            Mocks controller by label. Can only be used to test controllers
            that get instantiated automatically by cement.
            @param plugin_label e.g. 'drupal'
            @param method e.g. 'enumerate_plugins'
            @param return_value what to return. Default is None, unless the
                method starts with enumerate_*, in which case the result is a
                tuple as expected by BasePlugin.
            @param side_effect if set to an exception, it will raise an
                exception.
        """
        m = MagicMock()
        if return_value:
            m.return_value = return_value
        else:
            if method.startswith("enumerate_"):
                m.return_value = ({"a":[]}, True)

        if side_effect:
            m.side_effect = side_effect

        setattr(backend.__handlers__['controller'][plugin_label], method, m)
        return m

    def add_argv(self, argv):
        """
            Concatenates list with self.app.argv.
        """
        self.app._meta.argv += argv

    def assert_called_contains(self, mocked_method, position, thing):
        """
            asserts that the parameter in position 'position' equals 'thing' in
            the first call to mocked_method.
            @param mocked_method
            @param position the position the argument is. It starts at 0 and
            discounts self. e.g. (self, a, b, c): position of b -> 1
        """
        try:
            first_call = mocked_method.call_args_list[0][0]
        except:
            assert False, 'Method not called.'
        assert first_call[position] == thing, "Parameter is not as expected."

    def respond_several(self, base_url, data_obj):
        for status_code in data_obj:
            for item in data_obj[status_code]:
                url = base_url % item
                responses.add(responses.HEAD, url,
                        body=str(status_code), status=status_code)


