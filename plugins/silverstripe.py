from cement.core import handler, controller
from plugins import BasePlugin
import requests
import common

class SilverStripe(BasePlugin):

    plugins_file = "plugins/drupal/wordlists/plugins"
    plugins_base_url = '%s/'

    themes_file = "plugins/drupal/wordlists/themes_1250"
    themes_base_url = '%s/'

    folder_url = "misc/"
    regular_file_url = "misc/drupal.js"
    module_readme_file = "README.txt"

    class Meta:
        label = 'silverstripe'

    @controller.expose(help='silverstripe related scanning tools')
    def silverstripe(self):
        self.enumerate_route()


def load():
    handler.register(SilverStripe)

