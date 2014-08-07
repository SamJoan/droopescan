from cement.core import handler, controller
from plugins import BasePlugin
import common

class Dnn(BasePlugin):

    versions_file = "plugins/dnn/versions.xml"

    can_enumerate_themes = False
    can_enumerate_plugins = False

    class Meta:
        label = 'dnn'

    @controller.expose(help='dnn related scanning tools')
    def dnn(self):
        self.enumerate_route()

def load():
    handler.register(Dnn)

