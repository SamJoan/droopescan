from cement.core import handler, controller
from cement import Controller, ex
from dscan.common.plugins_util import Plugin, plugins_get
from dscan.common.functions import version_get
from dscan.common import template

class Stats(Controller):

    class Meta:
        label = 'stats'

    @ex(help='shows scanner status & capabilities.')
    def stats(self):
        plugins = plugins_get()
        version = version_get()

        print(template('stats_plugin.mustache', {'version': version,
            'plugins': plugins}))

def load(app=None):
    app.handler.register(Stats)

