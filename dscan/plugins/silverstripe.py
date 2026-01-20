from cement.core import handler, controller
from cement import ex
from concurrent.futures import ThreadPoolExecutor
from dscan import common
from dscan.plugins import BasePlugin
from requests.exceptions import ConnectionError
import dscan.common.update_api as ua
import re
import requests
import sys
try:
    import exceptions
except ImportError:
    pass

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
    update_majors = ['3.1', '3.0', '3.2', '3.3', '3.4', '2.4', '4.0', '4.1', '4.2', '4.3', '4.4', '4.6', '4.7', '4.8', '5.0', '5.1', '5.2', '6.0', '6.1']

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

    @ex(help='silverstripe related scanning tools')
    def silverstripe(self):
        self.plugin_init()

    @ex(help='alias for "silverstripe"', hide=True)
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
            try:
                cms_gr.tag_checkout(version)
            except exceptions.RuntimeError:
                print("Version %s does not exist on `cms` branch. Skipping." % version)
                continue

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

    def enumerate_version_from_html(self, url, timeout=15, headers={}):
        """
        Extract exact version from HTML meta generator tag.

        @param url: the base URL to check
        @param timeout: request timeout in seconds
        @param headers: headers to pass to requests.get()
        @return: version string (e.g., "6.1") or None if not found
        """
        try:
            response = self.session.get(url, timeout=timeout, headers=headers, verify=False)

            if response.status_code in [200, 403]:
                # Pattern matches: <meta name="generator" content="Silverstripe CMS 6.1">
                pattern = r'meta\s+name=["\']generator["\']\s+content=["\']Silverstripe\s+CMS\s+([0-9.]+)["\']'
                match = re.search(pattern, response.text, re.IGNORECASE)

                if match:
                    return match.group(1)

        except Exception:
            pass

        return None

    def enumerate_version(self, url, threads=10, verb='head',
            timeout=15, hide_progressbar=False, headers={}, no_fingerprint_fallback=False):
        """
        Override parent method to try HTML parsing first, then fall back to fingerprinting.

        @param url: the url to check
        @param threads: number of threads for fingerprinting
        @param verb: HTTP verb to use
        @param timeout: request timeout in seconds
        @param hide_progressbar: whether to hide progress bar
        @param headers: headers to pass to requests
        @param no_fingerprint_fallback: if True, only use file fingerprinting (no HTML fallbacks)
        @return: (possible_versions, is_empty)
        """
        # Always do fingerprinting
        fingerprint_versions, is_empty = super(Silverstripe, self).enumerate_version(
            url, threads, verb, timeout, hide_progressbar, headers, no_fingerprint_fallback
        )

        # If no_fingerprint_fallback mode is enabled, return fingerprint results without HTML fallbacks
        if no_fingerprint_fallback:
            return fingerprint_versions, is_empty

        # Try to get exact version from HTML generator tag
        html_version = self.enumerate_version_from_html(url, timeout, headers)

        if html_version:
            # Filter fingerprint versions that start with the HTML version
            # We want to match "6.1" against "6.1.0", "6.1.1", "6.1.0-beta1"
            # But NOT "6.10.0"
            filtered_versions = [
                v for v in fingerprint_versions
                if v == html_version or v.startswith(html_version + '.') or v.startswith(html_version + '-')
            ]

            if filtered_versions:
                return filtered_versions, False

            # If fingerprinting returned nothing, but we have HTML version, return HTML version
            if not fingerprint_versions:
                return [html_version], False

            # HTML version conflicts with fingerprinting - trust fingerprinting
            return fingerprint_versions, is_empty

        return fingerprint_versions, is_empty

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
    app.handler.register(Silverstripe)

