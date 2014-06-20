from cement.core import handler, controller
from plugins import BasePlugin
import requests
import common

class Dnn(BasePlugin):

    #plugins_file = None
    #plugins_base_url = None

    #themes_file = None
    #themes_base_url = None

    #folder_url = None
    #regular_file_url = None
    #module_readme_file = None

    # no changelog file for SS
    changelog = None
    versions_file = "plugins/dnn/versions.xml"

    class Meta:
        label = 'dnn'

    @controller.expose(help='dnn related scanning tools')
    def dnn(self):
        available = {
            'p': False,
            't': False,
        }
        self.enumerate_route(available)


def load():
    handler.register(Dnn)

