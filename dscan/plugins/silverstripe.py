from cement.core import handler, controller
from plugins import BasePlugin
import common
import common.update_api as ua

class SilverStripe(BasePlugin):

    plugins_file = 'plugins/silverstripe/wordlists/plugins'
    plugins_base_url = '%s%s/'

    themes_file = 'plugins/silverstripe/wordlists/themes'
    themes_base_url = '%sthemes/%s/'

    forbidden_url = 'framework/'
    regular_file_url = ['cms/css/layout.css', 'framework/css/UploadField.css']
    module_common_file = 'README.md'

    versions_file = 'plugins/silverstripe/versions.xml'

    interesting_urls = [
            ('framework/docs/en/changelogs/index.md', 'Changelogs, there are other files in same dir, but \'index.md\' is frequently outdated.'),
            ('Security/login', 'Administrative interface.')
        ]

    interesting_module_urls = [
        ('README.md', 'Default README file'),
        ('LICENSE', 'Default license file'),
        ('CHANGELOG', 'Default changelog file'),
    ]

    update_majors = ['3.1', '3.0', '2.4']
    _repo_framework = 'silverstripe/silverstripe-framework/'
    _repo_cms = 'silverstripe/silverstripe-cms/'

    class Meta:
        label = 'silverstripe'

    @controller.expose(help='silverstripe related scanning tools')
    def silverstripe(self):
        self.plugin_init()

    @controller.expose(help='alias for "silverstripe"')
    def ss(self):
        self.silverstripe()

    def update_version_check(self):
        """
            @return True if new tags have been made in the github repository.
        """
        return ua.github_tags_newer(self._repo_framework, self.versions_file,
                update_majors=self.update_majors)

    def update_version(self):
        """
            @return updated VersionsFile
        """
        fw_gr, versions_file, new_tags = ua.github_repo_new(self._repo_framework,
                'silverstripe/framework', self.versions_file, self.update_majors)
        cms_gr, _, _ = ua.github_repo_new(self._repo_cms,
                'silverstripe/cms', self.versions_file, self.update_majors)

        hashes = {}
        for version in new_tags:
            fw_gr.tag_checkout(version)
            cms_gr.tag_checkout(version)

            hashes[version] = ua.hashes_get(versions_file, self.update_majors, './.update-workspace/silverstripe/')

        versions_file.update(hashes)
        return versions_file

def load():
    handler.register(SilverStripe)

