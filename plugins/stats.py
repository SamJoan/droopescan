from cement.core import handler, controller
from common.plugins_util import Plugin, plugins_get
from common import template

class Stats(controller.CementBaseController):

    class Meta:
        label = 'stats'

    @controller.expose(help='shows scanner status & capabilities')
    def stats(self):
       plugins = plugins_get()
       for plugin in plugins:
           print(template('stats_plugin.tpl', {'plugin': plugin}))

def load():
    handler.register(Stats)

