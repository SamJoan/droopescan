from cement.core import handler, controller
from plugins import BasePlugin
from common.update_api import GitRepo
import common.update_api as ua
import common.versions

class Drupal(BasePlugin):

    plugins_file = "plugins/drupal/wordlists/plugins_3500"
    plugins_base_url = ["%ssites/all/modules/%s/",
            "%ssites/default/modules/%s/"]

    themes_file = "plugins/drupal/wordlists/themes_1250"
    themes_base_url = ["%ssites/all/themes/%s/",
            "%ssites/default/themes/%s/"]

    forbidden_url = "sites/"
    regular_file_url = ["misc/drupal.js", 'core/misc/drupal.js']
    module_common_file = "LICENSE.txt"

    interesting_urls = [
            ("CHANGELOG.txt", "Default changelog file"),
            ("user/login", "Default admin"),
        ]

    interesting_module_urls = [
        ('CHANGELOG.txt', 'Changelog file'),
        ('changelog.txt', 'Changelog file'),
        ('CHANGELOG.TXT', 'Changelog file'),
        ('README.txt', 'README file'),
        ('readme.txt', 'README file'),
        ('README.TXT', 'README file'),
        ('LICENSE.txt', 'License file'),
        ('API.txt', 'Contains API documentation for the module')
    ]

    versions_file = "plugins/drupal/versions.xml"
    update_majors = ['6','7','8']

    class Meta:
        label = 'drupal'

    @controller.expose(help='drupal-related scanning tools')
    def drupal(self):
        self.plugin_init()

    def update_version_check(self):
        """
            @return True if new tags have been made in the github repository.
        """
        return ua.github_tags_newer('drupal/drupal/', self.versions_file,
                update_majors=self.update_majors)

    def update_version(self):
        """
            @return updated VersionsFile
        """
        gr, versions_file, new_tags = ua.github_repo_new('drupal/drupal/',
                'drupal/drupal', self.versions_file, self.update_majors)

        hashes = {}
        for version in new_tags:
            gr.tag_checkout(version)
            hashes[version] = gr.hashes_get(versions_file, self.update_majors)

        versions_file.update(hashes)
        return versions_file

def load():
    handler.register(Drupal)

