from cement.core import handler, controller
from plugins import BasePlugin
import requests
import common

class Drupal(BasePlugin):

    plugins_file = "plugins/drupal/wordlists/top_1000"
    base_url = "%ssites/all/modules/%s/"

    class Meta:
        label = 'drupal'

    @controller.expose(help='drupal-related scanning tools')
    def drupal(self):
        self.enumerate_route()

    def enumerate_plugins(self, url):
        # TODO: detect how directories being present is being handled.
            # a) directory 403 -> detectable || DONE
            # b) directory 404 -> problem, can work around by requesting other
                # file, which one? e.g. a2dismod autoindex
            # c) directory == 200, directory listing.
        # TODO other module directories. (make configurable.)
        common.echo("Scanning...")
        plugins = self.plugins_get()
        found_plugins = []
        for plugin in plugins:
            r = requests.get(self.base_url % (url, plugin))
            if r.status_code == 403:
                found_plugins.append(plugin)

        return found_plugins

    def plugins_get(self):
        f = open(self.plugins_file)
        for plugin in f:
            yield plugin.strip()

def load():
    handler.register(Drupal)

