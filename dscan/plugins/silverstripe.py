from cement.core import handler, controller
from plugins import BasePlugin
import common
import common.update_api as ua
import re
import requests

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

    def update_plugins_check(self):
        return ua.update_modules_check(self)

    def update_plugins(self):
        plugins_url = 'http://addons.silverstripe.org/add-ons?search=&type=module&sort=downloads&start=%s'
        themes_url = 'http://addons.silverstripe.org/add-ons?search=&type=theme&sort=downloads&start=%s'
        css = '#layout > div.add-ons > table > tbody > tr > td > a'
        per_page = 16

        plugins = []
        for elem in ua.modules_get(plugins_url, per_page, css, pagination_type=ua.PT.skip):
            plugins.append(elem.string)

        themes = []
        for elem in ua.modules_get(themes_url, per_page, css, pagination_type=ua.PT.skip):
            themes.append(elem.string)

        notification = "Converting composer packages into folder names %s/2."
        print(notification % (1))
        plugins_folder = self._convert_to_folder(plugins)
        print(notification % (2))
        themes_folder = self._convert_to_folder(themes)

        return plugins_folder, themes_folder

    def _convert_to_folder(self, packages):
        """
            Silverstripe's page contains a list of composer packages. This
            function converts those to folder names. These may be different due
            to installer_name.
            @see https://github.com/composer/installers#custom-install-names
            @see https://github.com/richardsjoqvist/silverstripe-localdate/issues/7
        """
        folders = []
        url = 'https://packagist.org/p/%s.json'
        for package in packages:
            r = requests.get(url % package)
            if not 'installer-name' in r.text:
                folder_name = package.split('/')[1]
                folders.append(folder_name)
            else:
                splat = filter(None, re.split(r'[^a-z-]', r.text))
                installer_name = splat[splat.index('installer-name') + 1]
                folders.append(installer_name)

        return folders


def load():
    handler.register(SilverStripe)

