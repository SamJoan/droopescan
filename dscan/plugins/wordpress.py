from cement.core import handler, controller
from copy import deepcopy
from dscan.common.update_api import GitRepo
from dscan.plugins import BasePlugin
import dscan.common.update_api as ua
import dscan.common.versions
import requests

class Wordpress(BasePlugin):
    plugins_base_url = "%swp-content/plugins/%s/"
    themes_base_url = "%swp-content/themes/%s/"

    forbidden_url = "wp-includes/"
    regular_file_url = ["wp-admin/wp-admin.css", "wp-includes/js/tinymce/tiny_mce_popup.js"]
    module_common_file = "readme.txt"
    update_majors = ['2','3','4']

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
    @controller.expose(help='wordpress related scanning tools')
    def wordpress(self):
        self.plugin_init()

    @controller.expose(help='alias for "wordpress"', hide=True)
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

def load(app=None):
    handler.register(Wordpress)

