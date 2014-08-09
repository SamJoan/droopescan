from cement.core import handler, controller
from common.plugins_util import Plugin, plugins_get

class Stats(controller.CementBaseController):

    class Meta:
        label = 'stats'

    @controller.expose(help='shows scanner status & capabilities')
    def stats(self):
       plugins = plugins_get()
       print plugins

def load():
    handler.register(Stats)

