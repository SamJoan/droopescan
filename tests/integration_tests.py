from cement.utils import test
from plugins.versions import DrupalVersions, SSVersions
from tempfile import mkdtemp
from tests import BaseTest
import os

class IntegrationTests(BaseTest):
    '''
        Tests related to version fingerprinting for all plugins.
    '''

    def setUp(self):
        super(IntegrationTests, self).setUp()
        self.dv = DrupalVersions()
        self.file = mkdtemp() + "/"

    def test_get_newer_versions_by_major(self):
        sample_majors = {'7': '7.28', '6': '6.31'}
        higher = self.dv.newer_get(sample_majors)

    def test_get_newer_ss(self):
        self.dv = SSVersions()
        sample_majors = {'3': '3.1.5'}
        higher = self.dv.newer_get(sample_majors)

    def test_download_and_extract(self):
        # comments necessary for dbg
        newer = {'7': [('7.31', 'http://ftp.drupal.org/files/projects/drupal-7.31.tar.gz')], '6': [('6.33', 'http://ftp.drupal.org/files/projects/drupal-6.33.tar.gz')]}
        files = self.dv.download(newer, self.file)

        #files = [('7.31', '/var/www/drupal/7.31.tar.gz'), ('7.30', '/var/www/drupal/7.30.tar.gz'), ('7.29', '/var/www/drupal/7.29.tar.gz'), ('6.33', '/var/www/drupal/6.33.tar.gz'), ('6.32', '/var/www/drupal/6.32.tar.gz')]
        extracted_folders = self.dv.extract(files, self.file)

        #extracted_folders = [('7.31', '/var/www/drupal/drupal-7.31/'), ('7.30', '/var/www/drupal/drupal-7.30/'), ('7.29', '/var/www/drupal/drupal-7.29/'), ('6.33', '/var/www/drupal/drupal-6.33/'), ('6.32', '/var/www/drupal/drupal-6.32/')]
        exist_files = ['misc/drupal.js', 'misc/tabledrag.js', 'misc/tableheader.js', 'misc/ajax.js']

        out_sums = self.dv.sums_get(extracted_folders, exist_files)
        print(out_sums)

