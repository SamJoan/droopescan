from cement.core import handler, controller
from cement import ex
from copy import deepcopy
from dscan.common.update_api import GitRepo
from dscan.plugins import BasePlugin
import dscan.common.update_api as ua
import dscan.common.versions
import requests
import re

class Wordpress(BasePlugin):
    plugins_base_url = "%swp-content/plugins/%s/"
    themes_base_url = "%swp-content/themes/%s/"

    forbidden_url = "wp-includes/"
    regular_file_url = ["wp-admin/wp-admin.css", "wp-includes/js/tinymce/tiny_mce_popup.js"]
    module_common_file = "readme.txt"
    update_majors = ['2','3','4', '5']

    interesting_urls = [("readme.html", "This CMS' default changelog.")]

    interesting_module_urls = [
        ('readme.html', 'Default readme file.'),
        ('readme.txt', 'Default readme file.'),
        ('license.txt', 'License file.'),
        ('documentation.txt', 'Documentation file.'),
        ('screenshot.png', 'Screenshot for theme.'),
        ('screenshot-1.png', 'Screenshot for plugin. Sometimes increasing the number yields additional images.'),
    ]

    plugins_url = 'http://api.wordpress.org/plugins/info/1.1/'
    # plugins_url = 'http://requestb.in/11fb60y1'
    themes_url = 'http://api.wordpress.org/themes/info/1.1/'

    class Meta:
        # The label is important, choose the CMS name in lowercase.
        label = 'wordpress'

    # This function is the entry point for the CMS.
    @ex(help='wordpress related scanning tools')
    def wordpress(self):
        self.plugin_init()

    @ex(help='alias for "wordpress"', hide=True)
    def wp(self):
        self.wordpress()

    def update_version_check(self):
        """
        @return: True if new tags have been made in the github repository.
        """
        return ua.github_tags_newer('wordpress/wordpress/', self.versions_file,
                update_majors=self.update_majors)

    def update_version(self):
        """
        @return: updated VersionsFile
        """
        gr, versions_file, new_tags = ua.github_repo_new('wordpress/wordpress/',
                'wordpress/wordpress/', self.versions_file, self.update_majors)

        hashes = {}
        for version in new_tags:
            gr.tag_checkout(version)
            hashes[version] = gr.hashes_get(versions_file)

        versions_file.update(hashes)
        return versions_file

    def update_plugins_check(self):
        return ua.update_modules_check(self)

    def update_plugins(self):
        base_data = open(dscan.PWD + 'plugins/wordpress/base_api_request.txt')\
                .read()
        plugins_data = 'action=query_plugins&' + base_data
        themes_data = 'action=query_themes&' + base_data

        plugins = []
        response = ua.multipart_parse_json(self.plugins_url, data=plugins_data)
        for plugin in response['plugins']:
            plugins.append(plugin['slug'])

        themes = []
        response = ua.multipart_parse_json(self.themes_url, data=themes_data)
        for theme in response['themes']:
            themes.append(theme['slug'])

        return plugins, themes

    def enumerate_version_from_html(self, url, timeout=15, headers={}):
        """
        Extract exact version from HTML meta generator tag.

        @param url: the base URL to check
        @param timeout: request timeout in seconds
        @param headers: headers to pass to requests.get()
        @return: version string (e.g., "6.9") or None if not found
        """
        try:
            response = self.session.get(url, timeout=timeout, headers=headers, verify=False)

            if response.status_code in [200, 403]:
                # Pattern matches: <meta name="generator" content="WordPress 6.9" />
                pattern = r'meta\s+name=["\']generator["\']\s+content=["\']WordPress\s+([0-9.]+)["\']'
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
        fingerprint_versions, is_empty = super(Wordpress, self).enumerate_version(
            url, threads, verb, timeout, hide_progressbar, headers, no_fingerprint_fallback
        )

        # If no_fingerprint_fallback mode is enabled, return fingerprint results without HTML fallbacks
        if no_fingerprint_fallback:
            return fingerprint_versions, is_empty

        # Try to get exact version from HTML generator tag
        html_version = self.enumerate_version_from_html(url, timeout, headers)

        if html_version:
            # If we found a version in HTML, check if it's consistent with fingerprinting
            if not fingerprint_versions or html_version in fingerprint_versions:
                # HTML version is consistent, use it as the definitive answer
                return [html_version], False
            else:
                # HTML version conflicts with fingerprinting - trust fingerprinting
                return fingerprint_versions, is_empty

        return fingerprint_versions, is_empty

def load(app=None):
    app.handler.register(Wordpress)

