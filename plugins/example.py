from cement.core import handler, controller
from plugins import BasePlugin
import requests
import common

class Example(BasePlugin):

    # a file containing a list of plugins, one per line.
    plugins_file = "plugins/drupal/wordlists/plugins_3500"
    # the location of the plugins. If there are multiple locations, such as in
    # drupal, you can specify a list. First %s will be replaced with the site
    # url and the second will be replaced with the module name.
    plugins_base_url = ["%ssites/all/modules/%s/",
            "%ssites/default/modules/%s/"]
    # same as above
    themes_file = "plugins/drupal/wordlists/themes_1250"
    themes_base_url = ["%ssites/all/themes/%s/",
            "%ssites/default/themes/%s/"]
    # a URL which you know is a valid folder
    folder_url = "misc/"
    # a URL which you know results in a 200 OK. If item is a list, then all
    # items are tested to see if any responds with OK.
    regular_file_url = "misc/drupal.js"
    # a file which always exists in the modules.
    module_readme_file = "README.txt"

    class Meta:
        label = 'example'

    @controller.expose(help='example scanner')
    def example(self):
        # this calls BasePlugin.ennumerate_route.
        self.enumerate_route()

    # there is a plethora of functions to override in BasePlugin.

def load():
    handler.register(Example)

