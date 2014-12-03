from cement.core import handler, controller
from plugins import BasePlugin
from common.update_api import github_tag_newer

class Drupal(BasePlugin):

    plugins_file = "plugins/drupal/wordlists/plugins_3500"
    plugins_base_url = ["%ssites/all/modules/%s/",
            "%ssites/default/modules/%s/"]

    themes_file = "plugins/drupal/wordlists/themes_1250"
    themes_base_url = ["%ssites/all/themes/%s/",
            "%ssites/default/themes/%s/"]

    folder_url = "misc/"
    regular_file_url = "misc/drupal.js"
    module_readme_file = "LICENSE.txt"

    interesting_urls = [
            ("CHANGELOG.txt", "Default changelog file."),
            ("user/login", "Default admin."),
        ]
    versions_file = "plugins/drupal/versions.xml"

    class Meta:
        label = 'drupal'

    @controller.expose(help='drupal-related scanning tools')
    def drupal(self):
        self.plugin_init()

    def update_version_check(self):
        return github_tag_newer('drupal/drupal/', self.versions_file, update_majors=['6', '7'])

    def update_version(self):
        pass

def load():
    handler.register(Drupal)

