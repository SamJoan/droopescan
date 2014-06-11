from cement.core import handler, controller
from plugins import BasePlugin
import requests
import common

class SilverStripe(BasePlugin):

    # a file containing a list of plugins, one per line.
    plugins_file = "plugins/silverstripe/wordlists/top_1000"

    # plugins are in the root.
    base_url = "%s/"

    module_readme_file = "README.md"

    folder_url = "framework/"

    regular_file_url = ["framework/css/UploadField.css", "cms/css/layout.css"]

    class Meta:
        label = 'silverstripe'

    @controller.expose(help='silverstripe related scanning tools')
    def silverstripe(self):
        self.enumerate_route()


def load():
    handler.register(SilverStripe)

