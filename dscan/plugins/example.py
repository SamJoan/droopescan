"""
    A sample base plugin. Do not forget to add an init file in plugins.d
"""
from cement.core import handler, controller
from plugins import BasePlugin
import common

class Example(BasePlugin):
    # a file containing a list of plugins, one per line.
    plugins_file = "plugins/drupal/wordlists/plugins_3500"
    # the location of the plugins. If there are multiple locations, such as in
    # drupal, you can specify a list. First %s will be replaced with the site
    # url and the second will be replaced with the module name.
    plugins_base_url = ["%ssites/all/modules/%s/",
            "%ssites/default/modules/%s/"]
    # same as above
    themes_file = "plugins/drupal/wordlists/themes_1250"
    themes_base_url = ["%ssites/all/themes/%s/",
            "%ssites/default/themes/%s/"]
    # a URL which commonly responds with forbidden (most frequently folders, but
    # could be something else.)
    forbidden_url = "misc/"
    # a URL which you know results in a 200 OK. If item is a list, then all
    # items are tested to see if any responds with OK.
    regular_file_url = "misc/drupal.js"
    # a file which always exists in the modules.
    module_common_file = "README.txt"

    # a list of tuples that contain on the index 0 a url, and on 1 a description
    # to be shown to the user if the URL replies with 200 found
    interesting_urls = [("CHANGELOG", "This CMS' default changelog 200 OK.")]

    # A list of interesting files which are normally present in modules,
    # relative to the module's folder.
    interesting_module_urls = [
        ('CHANGELOG.txt', 'Changelog file'),
    ]

    # a file which validates against common/versions.xsd for version
    # fingerprinting.
    versions_file = "plugins/drupal/versions.xml"


    class Meta:
        label = 'example'

    @controller.expose(help='example scanner')
    def example(self):
        self.plugin_init()

    def update_version_check(self):
        """
            @return True if new versions of this software have been found.
        """

    def update_version(self):
        """
            This function needs to return an updated VersionsFile, which will
                be written to disk. There are APIs on common.update_api which can
                be used.
            @return updated VersionsFile
        """

    # there is a plethora of functions to override in BasePlugin and BaseInternalPlugin.

def load():
    handler.register(Example)

