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
        # comments necessary for dbg
        newer = {'7': [('7.31', 'http://ftp.drupal.org/files/projects/drupal-7.31.tar.gz'), ('7.30', 'http://ftp.drupal.org/files/projects/drupal-7.30.tar.gz'), ('7.29', 'http://ftp.drupal.org/files/projects/drupal-7.29.tar.gz')], '6': [('6.33', 'http://ftp.drupal.org/files/projects/drupal-6.33.tar.gz'), ('6.32', 'http://ftp.drupal.org/files/projects/drupal-6.32.tar.gz')]}
        files = self.dv.download(newer, BASE_FOLDER)
        #files = [('7.31', '/var/www/drupal/7.31.tar.gz'), ('7.30', '/var/www/drupal/7.30.tar.gz'), ('7.29', '/var/www/drupal/7.29.tar.gz'), ('6.33', '/var/www/drupal/6.33.tar.gz'), ('6.32', '/var/www/drupal/6.32.tar.gz')]
        extracted_folders = self.dv.extract(files, BASE_FOLDER)
        #extracted_folders = [('7.31', '/var/www/drupal/drupal-7.31/'), ('7.30', '/var/www/drupal/drupal-7.30/'), ('7.29', '/var/www/drupal/drupal-7.29/'), ('6.33', '/var/www/drupal/drupal-6.33/'), ('6.32', '/var/www/drupal/drupal-6.32/')]
        exist_files = ['misc/drupal.js', 'misc/tabledrag.js', 'misc/tableheader.js', 'misc/ajax.js']

        out_sums = self.dv.sums_get(extracted_folders, exist_files)
        print out_sums

    def test_add_to_xml(self):
        {'6.32': {'misc/drupal.js': '1904f6fd4a4fe747d6b53ca9fd81f848',
            'misc/tabledrag.js': '50ebbc8dc949d7cb8d4cc5e6e0a6c1ca',
            'misc/tableheader.js': '570b3f821441cd8f75395224fc43a0ea'}, '7.30':
            {'misc/ajax.js': '30d9e08baa11f3836eca00425b550f82',
                'misc/drupal.js': '0bb055ea361b208072be45e8e004117b',
                'misc/tabledrag.js': 'caaf444bbba2811b4fa0d5aecfa837e5',
                'misc/tableheader.js': 'bd98fa07941364726469e7666b91d14d'},
            '7.31': {'misc/ajax.js': '30d9e08baa11f3836eca00425b550f82',
                'misc/drupal.js': '0bb055ea361b208072be45e8e004117b',
                'misc/tabledrag.js': 'caaf444bbba2811b4fa0d5aecfa837e5',
                'misc/tableheader.js': 'bd98fa07941364726469e7666b91d14d'},
            '7.29': {'misc/ajax.js': '30d9e08baa11f3836eca00425b550f82',
                'misc/drupal.js': '0bb055ea361b208072be45e8e004117b',
                'misc/tabledrag.js': 'caaf444bbba2811b4fa0d5aecfa837e5',
                'misc/tableheader.js': 'bd98fa07941364726469e7666b91d14d'},
            '6.33': {'misc/drupal.js': '1904f6fd4a4fe747d6b53ca9fd81f848',
                'misc/tabledrag.js': '50ebbc8dc949d7cb8d4cc5e6e0a6c1ca',
                'misc/tableheader.js': '570b3f821441cd8f75395224fc43a0ea'}}

