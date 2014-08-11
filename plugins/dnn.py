from cement.core import handler, controller
from plugins import BasePlugin
import common

class Dnn(BasePlugin):

    versions_file = "plugins/dnn/versions.xml"

    can_enumerate_themes = False
    can_enumerate_plugins = False
    can_enumerate_interesting = False

    class Meta:
        label = 'dnn'

    @controller.expose(help='dnn related scanning tools')
    def dnn(self):
        self.plugin_init()

def load():
    handler.register(Dnn)

