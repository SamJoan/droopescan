from cement.core import handler, controller
from plugins import BasePlugin
import requests

class DrupalScanner(BasePlugin):

    class Meta:
        label = 'drupalscanner'

    @controller.expose(help='drupal-related scanning tools')
    def drupal(self):
        self.enumerate_route()

    def enumerate_plugins(self, url):
        plugins = self.modules_get()
        found_plugins = []
        for plugin in plugins:
            r = requests.get("%ssites/all/modules/%s/" % (url, plugin))
            if r.status_code == 403:
                found_plugins.append(plugin)

        return found_plugins

    def modules_get(self):
        return True

def load():
    handler.register(DrupalScanner)

