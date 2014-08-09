from cement.core import handler, controller
from plugins import BasePlugin
import common

class Stats(controller.CementBaseController):

    class Meta:
        label = 'stats'

    @controller.expose(help='shows scanner status & capabilities')
    def stats(self):
        pass

def load():
    handler.register(Stats)

