from cement.core import handler, controller
from common.update_api import github_tag_newer
from plugins import BasePlugin
import common

class SilverStripe(BasePlugin):

    plugins_file = 'plugins/silverstripe/wordlists/plugins'
    plugins_base_url = '%s%s/'

    themes_file = 'plugins/silverstripe/wordlists/themes'
    themes_base_url = '%sthemes/%s/'

    folder_url = 'framework/'
    regular_file_url = ['cms/css/layout.css', 'framework/css/UploadField.css']
    module_readme_file = 'README.md'

    versions_file = 'plugins/silverstripe/versions.xml'

    interesting_urls = [
            ('framework/docs/en/changelogs/index.md', 'Changelogs, there are other files in same dir, but \'index.md\' is frequently outdated.'),
            ('/Security/login', 'Administrative interface.')
        ]

    class Meta:
        label = 'silverstripe'

    @controller.expose(help='silverstripe related scanning tools')
    def silverstripe(self):
        self.plugin_init()

    def update_version_check(self):
        return github_tag_newer('silverstripe/silverstripe-framework/', self.versions_file, update_majors=['3.1', '3.0', '2'])

    def update_version(self):
        return False


def load():
    handler.register(SilverStripe)

