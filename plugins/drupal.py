from cement.core import handler, controller
from plugins import BasePlugin
import traceback
import mock
import sys

class DrupalScanner(BasePlugin):

    class Meta:
        label = 'drupalscanner'

    @controller.expose(help='drupal-related scanning tools')
    def drupal(self):
        self.enumerate_route()

    def enumerate_plugins(self, url):
        pass

def load():
    handler.register(DrupalScanner)

