from cement.core import handler, controller
from copy import deepcopy
from dscan.common.update_api import GitRepo
from dscan.plugins import BasePlugin
import dscan.common.update_api as ua
import dscan.common.versions
import requests

class Wordpress(BasePlugin):
    forbidden_url = "wp-includes/"
    regular_file_url = ["wp-admin/wp-admin.css", "wp-includes/js/tinymce/tiny_mce_popup.js"]
    module_common_file = ""

    update_majors = ['2','3','4']

    interesting_urls = [("readme.html", "This CMS' default changelog.")]

    interesting_module_urls = [
    ]

    plugins_url = 'http://api.wordpress.org/plugins/info/1.1/'
    themes_url = 'http://api.wordpress.org/themes/info/1.1/'

    class Meta:
        # The label is important, choose the CMS name in lowercase.
        label = 'wordpress'

    # This function is the entry point for the CMS.
    @controller.expose(help='wordpress related scanning tools')
    def wordpress(self):
        self.plugin_init()

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
            hashes[version] = gr.hashes_get(versions_file, self.update_majors)

        versions_file.update(hashes)
        return versions_file

    def update_plugins_check(self):
        return ua.update_modules_check(self)

    def update_plugins(self):
        base_data = {
            "request": {
                'browse': 'popular',
                'per_page': 1000, # Max provided.
                'field': {
                    'downloaded': False, 'rating': False, 'description': False,
                    'short_description': False, 'donate_link': False, 'tags':
                    False, 'sections': False, 'homepage': False, 'added': False,
                    'last_updated': False, 'compatibility': False, 'tested':
                    False, 'requires': False, 'downloadlink': False,
                }
            }
        }

        plugins_data = deepcopy(base_data)
        themes_data = deepcopy(base_data)
        plugins_data['action'] = 'query_plugins'
        themes_data['action'] = 'query_themes'

        plugins = []
        plugins_raw = ua.json_post(self.plugins_url, data=plugins_data)['plugins']
        for plugin in plugins_raw:
            plugins.append(plugin['slug'])

        themes = []
        themes_raw = ua.json_post(self.themes_url, data=themes_data)['themes']
        for theme in themes_raw:
            themes.append(theme['slug'])

        return plugins, themes

def load(app=None):
    handler.register(Wordpress)

