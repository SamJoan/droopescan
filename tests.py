from cement.utils import test
from droopescan import DroopeScan

class BaseTest(test.CementTestCase):
    app_class = DroopeScan

    def setUp(self):
        super(BaseTest, self).setUp()
        self.reset_backend()
        self.app = DroopeScan(argv=[],
            plugin_config_dir="./plugins.d",
            plugin_dir="./plugins")
        self.app.setup()

    def tearDown(self):
        self.app.close()

    def add_argv(self, argv):
        """
        Concatenates list with self.app.argv.
        """
        self.app._meta.argv += argv

class DroopeScanTest(BaseTest):
    """
        This class should contain tests which encompass all CMSs
    """

    @test.raises(RuntimeError)
    def test_errors_when_no_module(self):
        self.app.run()

class DrupalTest(BaseTest):
    """
        This class should contain tests specific to Drupal
    """

    def setUp(self):
        super(DrupalTest, self).setUp()
        self.add_argv(["drupal"])

    @test.raises(RuntimeError)
    def test_errors_when_no_url(self):
        self.app.run()

