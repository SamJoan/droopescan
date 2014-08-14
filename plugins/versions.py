from cement.core import handler, controller
from common import VersionsFile
from plugins.drupal import Drupal
from plugins import HumanBasePlugin
import os
import shutil
import sys

BASE_FOLDER = '/var/www/drupal/'

class Versions(HumanBasePlugin):
    class Meta:
        label = 'versions'

    @controller.expose(help='', hide=True)
    def versions(self):

        versions_file = VersionsFile(Drupal.versions_file)
        print versions_file.highest_version_major()
        sys.exit()

        ok = self.confirm('This will delete the contents of "%s"' % BASE_FOLDER)
        if ok:
            if os.path.isdir(BASE_FOLDER):
                shutil.rmtree(BASE_FOLDER)

            os.makedirs(BASE_FOLDER)
        else:
            self.error('Canceled by user.')

def load():
    handler.register(Versions)

