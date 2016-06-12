from cement.core import handler, controller
from concurrent.futures import ThreadPoolExecutor
from dscan import common
from dscan.plugins import BasePlugin
from requests.exceptions import ConnectionError
import dscan.common.update_api as ua
import re
import requests
import sys

try:
    from retrying import Retrying
except:
    pass

def _retry_msg(exception):
    if isinstance(exception, ConnectionError):
        print("Caught connection error, retrying.")
        return True
    else:
        return False

class Silverstripe(BasePlugin):

    plugins_base_url = '%s%s/'
    themes_base_url = '%sthemes/%s/'

    forbidden_url = 'framework/'
    regular_file_url = ['cms/css/layout.css', 'framework/css/UploadField.css',
            "framework/CONTRIBUTING.md"]
    module_common_file = 'README.md'
    update_majors = ['3.1', '3.0', '3.2', '3.3', '3.4', '2.4', '4.0']

    interesting_urls = [
            ('framework/docs/en/changelogs/index.md', 'Changelogs, there are other files in same dir, but \'index.md\' is frequently outdated.'),
            ('Security/login', 'Administrative interface.'),
            ('composer.json', 'Contains detailed, sensitive dependency information.'),
            ('vendor/composer/installed.json', 'Contains detailed, sensitive dependency information.'),
        ]

    interesting_module_urls = [
        ('README.md', 'Default README file'),
        ('LICENSE', 'Default license file'),
        ('CHANGELOG', 'Default changelog file'),
    ]

    _repo_framework = 'silverstripe/silverstripe-framework/'
    _repo_cms = 'silverstripe/silverstripe-cms/'

    class Meta:
        label = 'silverstripe'

    @controller.expose(help='silverstripe related scanning tools')
    def silverstripe(self):
        self.plugin_init()

    @controller.expose(help='alias for "silverstripe"', hide=True)
    def ss(self):
        self.silverstripe()

    def update_version_check(self):
        """
            @return: True if new tags have been made in the github repository.
        """
        return ua.github_tags_newer(self._repo_framework, self.versions_file,
                update_majors=self.update_majors)

    def update_version(self):
        """
            @return: updated VersionsFile
        """
        fw_gr, versions_file, new_tags = ua.github_repo_new(self._repo_framework,
                'silverstripe/framework', self.versions_file, self.update_majors)
        cms_gr, _, _ = ua.github_repo_new(self._repo_cms,
                'silverstripe/cms', self.versions_file, self.update_majors)

        hashes = {}
        for version in new_tags:
            fw_gr.tag_checkout(version)
            cms_gr.tag_checkout(version)

            hashes[version] = ua.hashes_get(versions_file, './.update-workspace/silverstripe/')

        versions_file.update(hashes)
        return versions_file

    def update_plugins_check(self):
        return ua.update_modules_check(self)

    def update_plugins(self):
        css = '#layout > div.add-ons > table > tbody > tr > td > a'
        per_page = 16
        plugins_url = 'http://addons.silverstripe.org/add-ons?search=&type=module&sort=downloads&start=%s'
        themes_url = 'http://addons.silverstripe.org/add-ons?search=&type=theme&sort=downloads&start=%s'
        update_amount = 2000

        plugins = []
        for elem in ua.modules_get(plugins_url, per_page, css, update_amount, pagination_type=ua.PT.skip):
            plugins.append(elem.string)

        themes = []
        for elem in ua.modules_get(themes_url, per_page, css, update_amount, pagination_type=ua.PT.skip):
            themes.append(elem.string)

        notification = "Converting composer packages into folder names %s/2."
        print(notification % (1))
        plugins_folder = self._convert_to_folder(plugins)
        print(notification % (2))
        themes_folder = self._convert_to_folder(themes)

        return plugins_folder, themes_folder

    def _get(self, url, package):
        retry = Retrying(wait_exponential_multiplier=2000, wait_exponential_max=120000,
            retry_on_exception=_retry_msg)

        return retry.call(requests.get, url % package)

    def _convert_to_folder(self, packages):
        """
            Silverstripe's page contains a list of composer packages. This
            function converts those to folder names. These may be different due
            to installer-name.

            Implemented exponential backoff in order to prevent packager from
            being overly sensitive about the number of requests I was making.

            @see: https://github.com/composer/installers#custom-install-names
            @see: https://github.com/richardsjoqvist/silverstripe-localdate/issues/7
        """
        url = 'http://packagist.org/p/%s.json'
        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = []
            for package in packages:
                future = executor.submit(self._get, url, package)
                futures.append({
                    'future': future,
                    'package': package
                })

            folders = []
            for i, future in enumerate(futures, start=1):
                r = future['future'].result()
                package = future['package']

                if not 'installer-name' in r.text:
                    folder_name = package.split('/')[1]
                else:
                    splat = list(filter(None, re.split(r'[^a-zA-Z0-9-_.,]', r.text)))
                    folder_name = splat[splat.index('installer-name') + 1]

                if not folder_name in folders:
                    folders.append(folder_name)
                else:
                    print("Folder %s is duplicated (current %s, previous %s)" % (folder_name,
                        package, folders.index(folder_name)))

                if i % 25 == 0:
                    print("Done %s." % i)

        return folders

def load(app=None):
    handler.register(Silverstripe)

