from cement.utils import test
from tests import BaseTest
from plugins.versions import DrupalVersions, BASE_FOLDER
import os

class IntegrationTests(BaseTest):
    '''
        Tests related to version fingerprinting for all plugins.
    '''

    def setUp(self):
        super(IntegrationTests, self).setUp()
        try:
            os.makedirs(BASE_FOLDER)
        except:
            pass
        self.dv = DrupalVersions()

    def test_get_newer_versions_by_major(self):
        sample_majors = {'7': '7.28', '6': '6.31'}
        higher = self.dv.newer_get(sample_majors)

    def test_download_and_extract(self):
        newer = {'7': [('7.31', 'http://ftp.drupal.org/files/projects/drupal-7.31.tar.gz'), ('7.30', 'http://ftp.drupal.org/files/projects/drupal-7.30.tar.gz'), ('7.29', 'http://ftp.drupal.org/files/projects/drupal-7.29.tar.gz')], '6': [('6.33', 'http://ftp.drupal.org/files/projects/drupal-6.33.tar.gz'), ('6.32', 'http://ftp.drupal.org/files/projects/drupal-6.32.tar.gz')]}
        files = self.dv.download(newer, BASE_FOLDER)
        files = [('7.31', '/var/www/drupal/7.31.tar.gz'), ('7.30', '/var/www/drupal/7.30.tar.gz'), ('7.29', '/var/www/drupal/7.29.tar.gz'), ('6.33', '/var/www/drupal/6.33.tar.gz'), ('6.32', '/var/www/drupal/6.32.tar.gz')]
        extracted_folders = self.dv.extract(files, BASE_FOLDER)

