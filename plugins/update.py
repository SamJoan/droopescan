from cement.core import handler, controller
from plugins import HumanBasePlugin
from common.plugins_util import plugins_base_get

class Update(HumanBasePlugin):
    class Meta:
        label = 'update'

    @controller.expose(help='', hide=True)
    def update(self):
        plugins = plugins_base_get()
        for Plugin in plugins:
            try:
                plugin = Plugin()
                plugin_name = plugin.Meta.label

                must_update = plugin.update_version_check()
                if must_update:
                    plugin.update_version()
                else:
                    self.msg('%s is up to date.' % plugin_name.capitalize())

            except AttributeError:
                self.msg('Skipping "%s" because update_version_check() or update_version() is not defined.' % plugin_name)

def load():
    handler.register(Update)
