from cement.core import handler, controller
from cement import ex
from dscan import common
from dscan.plugins import BasePlugin
import dscan.common.update_api as ua

class Moodle(BasePlugin):
    """
    Moodle scanning implementation. Thanks to @fede2cr.
    """
    plugins_base_url = ["%smod/%s/"]
    themes_base_url = ["%stheme/%s/"]

    forbidden_url = "cache/"
    regular_file_url = ['lib/javascript-static.js']
    module_common_file = "version.php"
    update_majors = ['2.7', '2.9', '3.0', '3.1', '3.2', '3.3']

    interesting_urls = [
        ("tags.txt", "A doc about creating tags."),
        ("README.txt", "Static readme file."),
        ("login/", "Admin panel")
    ]

    interesting_module_urls = [
        ('README.txt', 'Readme text file'),
        ('upgrade.txt', 'Upgrade text file'),
        ('readme.txt', 'Readme file (lowercase)'),
        ('README.md', 'Readme markdown file'),
        ('version.php', 'Version file'),
    ]

    class Meta:
        label = 'moodle'

    @ex(help='Moodle scanner')
    def moodle(self):
        self.plugin_init()

    def update_version_check(self):
        """
        @return: True if new versions of this software have been found.
        """
        return ua.github_tags_newer('moodle/moodle/', self.versions_file,
                update_majors=self.update_majors)

    def update_version(self):
        """
        @return: updated VersionsFile
        """
        gr, versions_file, new_tags = ua.github_repo_new('moodle/moodle/',
                'moodle/moodle', self.versions_file, self.update_majors)

        hashes = {}
        for version in new_tags:
            # tags look like "v1.0" in Moodle. 
            gr.tag_checkout("v" + version)
            hashes[version] = gr.hashes_get(versions_file)

        versions_file.update(hashes)
        return versions_file

    def update_plugins_check(self):
        pass

    def update_plugins(self):
        """
        This function needs to return two updated lists containing plugins
        and themes. There are APIs on common.update_api which can be used.
        @return: (plugins, themes)
        """

def load(app=None):
    app.handler.register(Moodle)

