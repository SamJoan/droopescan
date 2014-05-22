from cement.core import handler, controller
from plugins import BasePlugin
import requests

class DrupalScanner(BasePlugin):

    plugins_file = "plugins/drupal/wordlists/top_1000"

    class Meta:
        label = 'drupalscanner'

    @controller.expose(help='drupal-related scanning tools')
    def drupal(self):
        self.enumerate_route()

    def enumerate_plugins(self, url):
        plugins = self.plugins_get()
        found_plugins = []
        for plugin in plugins:
            r = requests.get("%ssites/all/modules/%s/" % (url, plugin))
            if r.status_code == 403:
                found_plugins.append(plugin)

        return found_plugins

    def plugins_get(self):
        f = open(self.plugins_file)
        for plugin in f:
            yield plugin

def load():
    handler.register(DrupalScanner)

