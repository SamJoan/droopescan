from __future__ import print_function
from cement.core import handler, controller
from plugins import HumanBasePlugin
import common.plugins_util as pu
import sys

class Update(HumanBasePlugin):
    class Meta:
        label = 'update'
        stacked_on = 'base'
        stacked_type = 'nested'
        hide = True
        arguments = [
            (['--skip-version'], dict(action='store_true', help='Skip version updates.',
                required=False, default=None)),
            (['--skip-modules'], dict(action='store_true', help='Skip module updates.',
                required=False, default=None)),
        ]

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
            self.msg('%s versions are up to date.' % plugin_name.capitalize())

    def update_plugins(self, plugin, plugin_name):
        try:
            must_update = plugin.update_plugins_check()
        except ValueError:
            must_update = True

        if must_update:
            self.msg("Updating plugins for %s..." % plugin_name)
            plugins, themes = plugin.update_plugins()

            with open(plugin.plugins_file, 'w') as f:
                for p in plugins:
                    f.write(p + "\n")

            with open(plugin.themes_file, 'w') as f:
                for t in themes:
                    f.write(t + "\n")

            self.msg("Successfully wrote %s plugins and %s themes." %
                    (len(plugins), len(themes)))

        else:
            self.msg('%s modules don\'t need updating.' % plugin_name.capitalize())

    @controller.expose(help='', hide=True)
    def default(self):
        plugins = pu.plugins_base_get()

        skip_version = self.app.pargs.skip_version
        skip_modules = self.app.pargs.skip_modules

        for Plugin in plugins:
            try:
                plugin = Plugin()
                plugin_name = plugin.Meta.label

                if not skip_version:
                    self.update_version(plugin, plugin_name)
                if not skip_modules:
                    self.update_plugins(plugin, plugin_name)

            except AttributeError:
                self.msg('Skipping %s because update_version_check() or update_version() is not defined.' % plugin_name)

def load(app=None):
    handler.register(Update)
