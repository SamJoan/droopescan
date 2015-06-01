from cement.core import handler, controller
from plugins import BasePlugin
import common

class Joomla(BasePlugin):
    forbidden_url = "misc/"
    regular_file_url = "misc/drupal.js"
    module_common_file = "README.txt"

    update_majors = ['1','2','3']

    interesting_urls = [("CHANGELOG", "This CMS' default changelog.")]

    interesting_module_urls = [
        ('CHANGELOG.txt', 'Changelog file'),
    ]

    class Meta:
        # The label is important, choose the CMS name in lowercase.
        label = 'joomla'

    # This function is the entry point for the CMS.
    @controller.expose(help='example scanner')
    def example(self):
        self.can_enumerate_plugins = False
        self.can_enumerate_themes = False
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
        pass

    def update_plugins_check(self):
        return False

    def update_plugins(self):
        pass

def load(app=None):
    handler.register(Joomla)

