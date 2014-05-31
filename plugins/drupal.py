from cement.core import handler, controller
from plugins import BasePlugin
import requests
import common

class Drupal(BasePlugin):

    plugins_file = "plugins/drupal/wordlists/top_1000"
    plugins_base_url = ["%ssites/all/modules/%s/",
            "%ssites/default/modules/%s/"]

    folder_url = "misc/"
    regular_file_url = "misc/drupal.js"
    module_readme_file = "README.txt"

    class Meta:
        label = 'drupal'

    @controller.expose(help='drupal-related scanning tools')
    def drupal(self):
        self.enumerate_route()

    def plugins_get(self):
        f = open(self.plugins_file)
        for plugin in f:
            yield plugin.strip()

def load():
    handler.register(Drupal)

