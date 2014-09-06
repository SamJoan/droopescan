from cement.core import handler, controller
from plugins import BasePlugin
import common

class Dnn(BasePlugin):

    interesting_urls = [
            ("Install/UpgradeWizard.aspx", "Upgrade wizard, version disclosure."),
            ("Install/InstallWizard.aspx", "Install wizard."),
            ('Home/tabid/36/ctl/Login/Default.aspx', 'Admin page.'),
            ('login', 'Admin page.')
        ]

    versions_file = "plugins/dnn/versions.xml"

    can_enumerate_themes = False
    can_enumerate_plugins = False

    class Meta:
        label = 'dnn'

    @controller.expose(help='dnn related scanning tools')
    def dnn(self):
        self.plugin_init()

def load():
    handler.register(Dnn)

