from cement.core import handler, controller
from plugins import BasePlugin
import requests
import common

class Example(BasePlugin):

    # a file containing a list of plugins, one per line.
    plugins_file = "plugins/drupal/wordlists/top_1000"

    # the location of the plugins. If there are multiple locations, such as in
    # drupal, you can specify a list. First %s will be replaced with the site
    # url and the second will be replaced with the module name.
    base_url = "%ssites/all/modules/%s/"
    #base_url = ["%ssites/all/modules/%s/",
            #"%ssites/default/modules/%s/"]

    # a file which always exists in the modules.
    module_readme_file = "README.txt"

    # a URL which you know is a valid folder
    folder_url = "misc/"

    # a URL which you know results in a 200 OK.
    regular_file_url = "misc/drupal.js"

    class Meta:
        label = 'example'

    @controller.expose(help='example scanner')
    def example(self):
        # this calls BasePlugin.ennumerate_route.
        self.enumerate_route()

    # there is a plethora of functions to override in BasePlugin.

def load():
    handler.register(Example)

