from cement.core import handler, controller
from dscan.plugins import BasePlugin
from dscan.common.update_api import GitRepo
import dscan.common.update_api as ua
import dscan.common.versions

class Drupal(BasePlugin):

    plugins_base_url = [
            "%ssites/all/modules/%s/",
            "%ssites/default/modules/%s/",
            "%smodules/%s/"]
    themes_base_url = [
            "%ssites/all/themes/%s/",
            "%ssites/default/themes/%s/",
            "%sthemes/%s/"]

    forbidden_url = "sites/"
    regular_file_url = ["misc/drupal.js", 'core/misc/drupal.js']
    module_common_file = "LICENSE.txt"
    update_majors = ['6','7','8']

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

    class Meta:
        label = 'drupal'

    @controller.expose(help='drupal related scanning tools')
    def drupal(self):
        self.plugin_init()

    def update_version_check(self):
        """
        @return: True if new tags have been made in the github repository.
        """
        return ua.github_tags_newer('drupal/drupal/', self.versions_file,
                update_majors=self.update_majors)

    def update_version(self):
        """
        @return: updated VersionsFile
        """
        gr, versions_file, new_tags = ua.github_repo_new('drupal/drupal/',
                'drupal/drupal', self.versions_file, self.update_majors)

        hashes = {}
        for version in new_tags:
            gr.tag_checkout(version)
            hashes[version] = gr.hashes_get(versions_file)

        versions_file.update(hashes)
        return versions_file

    def update_plugins_check(self):
        return ua.update_modules_check(self)

    def update_plugins(self):
        """
        @return: (plugins, themes) a tuple which contains two list of
            strings, the plugins and the themes.
        """
        plugins_url = 'https://drupal.org/project/project_module?page=%s'
        plugins_css = '.node-project-module > h2 > a'
        themes_url = 'https://drupal.org/project/project_theme?page=%s'
        themes_css = '.node-project-theme > h2 > a'
        per_page = 25

        plugins = []
        for elem in ua.modules_get(plugins_url, per_page, plugins_css):
            plugins.append(elem['href'].split("/")[-1])

        themes = []
        for elem in ua.modules_get(themes_url, per_page, themes_css):
            themes.append(elem['href'].split("/")[-1])

        return plugins, themes

def load(app=None):
    handler.register(Drupal)

