from cement.core import handler, controller
from dscan.plugins import BasePlugin
from dscan import common

class Moodle(BasePlugin):
    """
    A sample base plugin. Remember to create:
    In dscan/plugins.d/ an conf file.
    In dscan/plugins/<plugin_name>/ three files:
        - plugins.txt
        - themes.txt
        - versions.xml
    At the end of this file, a register call.
    """

    # the location of the plugins. If there are multiple locations, such as in
    # drupal, you can specify a list. First %s will be replaced with the site
    # url and the second will be replaced with the module name.
    plugins_base_url = ["%smod/%s/"]
    themes_base_url = ["%stheme/%s/"]

    # A URL which is known to usually be a folder.
    forbidden_url = "error/"
    # a URL which you know results in a 200 OK. If item is a list, then all
    # items are tested to see if any responds with OK.
    #regular_file_url = "behat.yml.dist"
    regular_file_url = "README.txt"
    # a file which commonly exists in the modules.
    module_common_file = "version.php"
    # Major branches which are supported by the vendor. This is used for
    # updating.
    update_majors = ['3']

    # a list of tuples that contain on the index 0 a url, and on 1 a description
    # to be shown to the user if the URL replies with 200 found
    interesting_urls = [("tags.txt", "A doc about creating tags.")]

    # A list of interesting files which are normally present in modules,
    # relative to the module's folder.
    interesting_module_urls = [
        ('README.txt', 'Readme text file'),
        ('upgrade.txt', 'Upgrade text file'),
        ('readme.txt', 'Readme file (lowercase)'),
        ('README.md', 'Readme markdown file'),
        ('version.php', 'Version file'),
    ]

    class Meta:
        # The label is important, choose the CMS name in lowercase.
        label = 'moodle'

    # This function is the entry point for the CMS.
    @controller.expose(help='Moodle scanner')
    def moodle(self):
        self.plugin_init()

    # The four functions below get called when ./droopescan update is called.
    # They can make use of dscan.common.update_api in order to update the
    # versions.xml and the *.txt files.
    #
    # See drupal and silverstripe for examples.
    def update_version_check(self):
        """
        @return: True if new versions of this software have been found.
        """

    def update_version(self):
        """
        This function needs to return an updated VersionsFile, which will be
        written to disk. There are APIs on common.update_api which can be
        used.
        @return: updated VersionsFile
        """

    def update_plugins_check(self):
        pass

    def update_plugins(self):
        """
        This function needs to return two updated lists containing plugins
        and themes. There are APIs on common.update_api which can be used.
        @return: (plugins, themes)
        """

def load(app=None):
    handler.register(Moodle)

