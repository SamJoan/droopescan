from cement.core import handler, controller
from plugins import BasePlugin
import requests
import common

class DotNetNuke(BasePlugin):

    #plugins_file = None
    #plugins_base_url = None

    #themes_file = None
    #themes_base_url = None

    #folder_url = None
    #regular_file_url = None
    #module_readme_file = None

    # no changelog file for SS
    changelog = None
    versions_file = "plugins/dotnetnuke/versions.xml"

    class Meta:
        label = 'dotnetnuke'

    @controller.expose(help='dotnetnuke related scanning tools')
    def dotnetnuke(self):
        self.enumerate_route()


def load():
    handler.register(DotNetNuke)

