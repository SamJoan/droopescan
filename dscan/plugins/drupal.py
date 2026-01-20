from cement.core import handler, controller
from cement import ex
from dscan.plugins import BasePlugin
from dscan.common.update_api import GitRepo
import dscan.common.update_api as ua
import dscan.common.versions
import re

class Drupal(BasePlugin):

    plugins_base_url = [
            "%ssites/all/modules/%s/",
            "%ssites/default/modules/%s/",
            "%smodules/contrib/%s/",
            "%smodules/%s/"]
    themes_base_url = [
            "%ssites/all/themes/%s/",
            "%ssites/default/themes/%s/",
            "%sthemes/%s/"]

    forbidden_url = "sites/"
    regular_file_url = ["misc/drupal.js", 'core/misc/drupal.js']
    module_common_file = "LICENSE.txt"
    update_majors = ['6','7','8', '9', '10', '11']

    interesting_urls = [
            ("CHANGELOG.txt", "Default changelog file"),
            ("user/login", "Default admin"),
        ]

    interesting_module_urls = [
        ('CHANGELOG.txt', 'Changelog file'),
        ('CHANGELOG.md', 'Changelog file'),
        ('changelog.txt', 'Changelog file'),
        ('CHANGELOG.TXT', 'Changelog file'),
        ('README.txt', 'README file'),
        ('README.md', 'README file'),
        ('readme.txt', 'README file'),
        ('README.TXT', 'README file'),
        ('LICENSE.txt', 'License file'),
        ('API.txt', 'Contains API documentation for the module')
    ]

    class Meta:
        label = 'drupal'

    @ex(help='drupal related scanning tools')
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

    def enumerate_version_from_html(self, url, timeout=15, headers={}):
        """
        Extract exact version from HTML query parameters or meta tags.
        Priority:
        1. Query parameters: ?v=X.Y.Z in asset URLs (Drupal 8+)
        2. Meta Generator tag: <meta name="Generator" content="Drupal X ..." />

        @param url: the base URL to check
        @param timeout: request timeout in seconds
        @param headers: headers to pass to requests.get()
        @return: tuple (version_string, source) or (None, None) if not found
                 source is 'query_param' or 'meta_generator'
        """
        try:
            # Don't follow redirects - we want the HTML from the target URL, not a redirect destination
            response = self.session.get(url, timeout=timeout, headers=headers, verify=False, allow_redirects=False)

            # Try to parse HTML even with non-200 status codes (some sites may return content)
            if response.status_code in [200, 403]:
                # Method 1: Query parameters (?v=X.Y.Z)
                # Pattern matches: /core/misc/drupal.js?v=11.2.10 or similar
                # Looks for ?v= followed by semantic version (X.Y.Z)
                pattern = r'\?v=(\d+\.\d+\.\d+)'
                match = re.search(pattern, response.text)

                if match:
                    return match.group(1), 'query_param'

                # Method 2: Meta Generator tag
                # Pattern matches: <meta name="Generator" content="Drupal 11 ..." />
                # Also handles variations like generator, GENERATOR, etc.
                generator_pattern = r'<meta\s+name=["\']?[Gg]enerator["\']?\s+content=["\']?Drupal\s+(\d+)'
                generator_match = re.search(generator_pattern, response.text)

                if generator_match:
                    # Extract major version and return it as X.0.0 format for consistency
                    major_version = generator_match.group(1)
                    return f"{major_version}.0.0", 'meta_generator'

        except Exception:
            # Silently fail and let fingerprinting handle it
            pass

        return None, None

    def enumerate_version(self, url, threads=10, verb='head',
            timeout=15, hide_progressbar=False, headers={}, no_fingerprint_fallback=False):
        """
        Override parent method with priority-based version detection:
        1. File fingerprinting (highest priority)
           - If returns single version: use it (definitive)
           - If returns multiple versions: use query parameter to disambiguate (unless no_fingerprint_fallback)
        2. HTML query parameters (?v=X.Y.Z) - used to narrow down multiple fingerprints (unless no_fingerprint_fallback)
        3. Meta Generator tag (backup/fallback) (disabled with no_fingerprint_fallback)

        @param url: the url to check
        @param threads: number of threads for fingerprinting
        @param verb: HTTP verb to use
        @param timeout: request timeout in seconds
        @param hide_progressbar: whether to hide progress bar
        @param headers: headers to pass to requests
        @param no_fingerprint_fallback: if True, only use file fingerprinting (no HTML fallbacks)
        @return: (possible_versions, is_empty)
        """
        # Priority 1: File fingerprinting (most accurate)
        fingerprint_versions, is_empty = super(Drupal, self).enumerate_version(
            url, threads, verb, timeout, hide_progressbar, headers, no_fingerprint_fallback
        )

        # If no_fingerprint_fallback mode is enabled, return fingerprint results without fallbacks
        if no_fingerprint_fallback:
            self.html_version_found = None
            self.html_version_source = None
            return fingerprint_versions, is_empty

        if fingerprint_versions:
            # Fingerprinting found versions
            if len(fingerprint_versions) == 1:
                # Single version found - definitive result (highest priority)
                self.html_version_found = None
                self.html_version_source = None
                return fingerprint_versions, is_empty
            else:
                # Multiple versions found - try to narrow down with query parameter method
                html_version, html_source = self.enumerate_version_from_html(url, timeout, headers)

                if html_version and html_source == 'query_param':
                    # Query parameter found - check if it matches one of the fingerprinted versions
                    if html_version in fingerprint_versions:
                        # Exact match - use query parameter to disambiguate
                        self.html_version_found = html_version
                        self.html_version_source = html_source
                        return [html_version], False
                    # Query parameter doesn't match fingerprints - trust fingerprinting

                # Return multiple fingerprinted versions (couldn't narrow down)
                self.html_version_found = None
                self.html_version_source = None
                return fingerprint_versions, is_empty

        # No fingerprinting results - try HTML methods (?v= parameter and meta Generator)
        html_version, html_source = self.enumerate_version_from_html(url, timeout, headers)

        if html_version:
            # HTML method found a version
            self.html_version_found = html_version
            self.html_version_source = html_source
            return [html_version], False

        # No version found by any method
        self.html_version_found = None
        self.html_version_source = None
        return fingerprint_versions, is_empty

def load(app=None):
    app.handler.register(Drupal)

