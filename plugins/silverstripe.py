from cement.core import handler, controller
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
        ]

    class Meta:
        label = 'silverstripe'

    @controller.expose(help='silverstripe related scanning tools')
    def silverstripe(self):
        self.plugin_init()


def load():
    handler.register(SilverStripe)

