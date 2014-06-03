from cement.core import handler, controller
from plugins import BasePlugin
import requests
import common

class Drupal(BasePlugin):

    plugins_file = "plugins/drupal/wordlists/plugins_3500"
    plugins_base_url = ["%ssites/all/modules/%s/",
            "%ssites/default/modules/%s/"]

    themes_file = "plugins/drupal/wordlists/themes_1250"
    themes_base_url = ["%ssites/all/themes/%s/",
            "%ssites/default/themes/%s/"]

    folder_url = "misc/"
    regular_file_url = "misc/drupal.js"
    module_readme_file = "README.txt"

    class Meta:
        label = 'drupal'

    @controller.expose(help='drupal-related scanning tools')
    def drupal(self):
        self.enumerate_route()

def load():
    handler.register(Drupal)

