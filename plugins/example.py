from cement.core import handler, controller
from plugins import BasePlugin
import requests
import common

class Example(BasePlugin):

    plugins_file = "plugins/drupal/wordlists/top_1000"
    # first %s gets replaced with site URL. Second with module name.
    base_url = "%ssites/all/modules/%s/"

    class Meta:
        label = 'example'

    @controller.expose(help='example scanner')
    def example(self):
        self.enumerate_route()

def load():
    handler.register(Example)

