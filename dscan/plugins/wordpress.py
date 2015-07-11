from cement.core import handler, controller
from common.update_api import GitRepo
from plugins import BasePlugin
import common.update_api as ua
import common.versions

class Wordpress(BasePlugin):
    can_enumerate_plugins = False
    can_enumerate_themes = False

    forbidden_url = "wp-includes/"
    regular_file_url = ["wp-admin/wp-admin.css", "wp-includes/js/tinymce/tiny_mce_popup.js"]
    module_common_file = ""

    update_majors = ['2','3','4']

    interesting_urls = [("readme.html", "This CMS' default changelog.")]

    interesting_module_urls = [
    ]

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
        return False

    def update_plugins(self):
        pass

def load(app=None):
    handler.register(Wordpress)

