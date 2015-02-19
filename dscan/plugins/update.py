from cement.core import handler, controller
from plugins import HumanBasePlugin
import common.plugins_util as pu


class Update(HumanBasePlugin):
    class Meta:
        label = 'update'

    def is_valid(self, new_xml):
        return new_xml.startswith('<cms>')

    def update_version(self, plugin, plugin_name):
        must_update = plugin.update_version_check()
        if must_update:
            new_vf = plugin.update_version()
            with open(plugin.versions_file, 'w') as f:
                new_xml = new_vf.str_pretty()
                if self.is_valid(new_xml):
                    f.write(new_xml)
                else:
                    self.msg('Prevented write of invalid XML %s' %
                            new_xml)

            self.msg('Updated %s.' % plugin_name)

        else:
            self.msg('%s is up to date.' % plugin_name.capitalize())

    def update_plugins(self, plugin, plugin_name):
        must_update = plugin.update_plugins_check()
        if must_update:
            plugins, themes = plugin.update_plugins()

            with open(plugin.plugins_file, 'w') as f:
                for p in plugins:
                    f.write(p + "\n")

            with open(plugin.themes_file, 'w') as f:
                for t in themes:
                    f.write(t + "\n")

        else:
            self.msg('%s is up to date.' % plugin_name.capitalize())

    @controller.expose(help='', hide=True)
    def update(self):
        plugins = pu.plugins_base_get()
        for Plugin in plugins:
            try:
                plugin = Plugin()
                plugin_name = plugin.Meta.label

                self.update_version(plugin, plugin_name)
                self.update_plugins(plugin, plugin_name)
            except AttributeError:
                self.msg('Skipping %s because update_version_check() or update_version() is not defined.' % plugin_name)

def load():
    handler.register(Update)
