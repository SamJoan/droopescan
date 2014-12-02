from cement.core import handler, controller
from plugins import HumanBasePlugin
from common.plugins_util import plugins_base_get

class Update(HumanBasePlugin):
    class Meta:
        label = 'update'

    @controller.expose(help='', hide=True)
    def update(self):
        plugins = plugins_base_get()
        for plugin in plugins:
            try:
                must_update = plugin.update_version_check()
                if must_update:
                    plugin.update_version()
            except AttributeError:
                print("Skipping '%s' because update_version_check() or update_version() is not defined." % plugin.Meta.label)

def load():
    handler.register(Update)
