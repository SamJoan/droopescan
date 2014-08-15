from bs4 import BeautifulSoup
from cement.core import handler, controller
from common import VersionsFile, version_gt, md5_file
from plugins.drupal import Drupal
from plugins import HumanBasePlugin
from subprocess import call
import tarfile
import os
import requests
import shutil
import sys

BASE_FOLDER = '/var/www/drupal/'
UPDATE_MAJORS = ['6', '7']

class DrupalVersions():

    def newer_get(self, majors):
        """
            get all versions higher than those provided, by major
            @param majors as returned by VersionsFile.latest_by_major
        """
        api_version = {'7': '103', '6': '87'}
        base_url = 'https://www.drupal.org/node/3060/release?api_version[]=%s'
        newer = {}
        for major in majors:
            max_avail = majors[major]
            api_ver = api_version[major]

            resp = requests.get(base_url % api_ver)
            soup = BeautifulSoup(resp.text)

            download_links = soup.select('.views-row-first .file a')

            for a in download_links:
                dl_url = a['href']
                if dl_url.endswith('.tar.gz'):
                    version = '.'.join(dl_url.split('-')[1].split('.')[0:-2])
                    if not version_gt(version, max_avail):
                        break

                    if not major in newer:
                        newer[major] = []

                    newer[major].append((version, dl_url))

        return newer

    def download(self, newer, location):
        """
            Download files that are new.
            @param newer as returned by self.newer_get
        """
        files = []
        for major in newer:
            urls = newer[major]
            for version, dl_url in urls:
                out_file = location + version + '.tar.gz'
                call(['wget', dl_url, '-O', out_file])
                files.append((version, out_file))

        return files

    def extract(self, files, location):
        """
            Extract downloaded files.
            @param tars as returned by self.download
        """
        extracted = []
        for version, tar_file in files:
            tar = tarfile.open(tar_file)
            extract_folder = os.path.commonprefix(tar.getnames())
            tar.extractall(path=location)

            extracted.append((version, location + extract_folder + "/"))

        return extracted

    def sums_get(self, extracted, files_to_hash):
        sums = {}
        for version, directory in extracted:
            sums[version] = {}
            for filename in files_to_hash:
                try:
                    sums[version][filename] = md5_file(directory + filename)
                except IOError:
                    # file doesn't exist.
                    pass

        return sums



class Versions(HumanBasePlugin):
    class Meta:
        label = 'versions'

    @controller.expose(help='', hide=True)
    def versions(self):
        dv = DrupalVersions()
        versions_file = VersionsFile(Drupal.versions_file)

        ok = self.confirm('This will delete the contents of "%s"' % BASE_FOLDER)
        if ok:
            if os.path.isdir(BASE_FOLDER):
                shutil.rmtree(BASE_FOLDER)

            os.makedirs(BASE_FOLDER)
            all_majors = versions_file.highest_version_major()
            majors = {key: all_majors[key] for key in UPDATE_MAJORS}

            new = dv.newer_get(majors)
            dl_files = dv.download(new, BASE_FOLDER)
            extracted_dirs = dv.extract(dl_files, BASE_FOLDER)

            file_sums = dv.sums_get(extracted_dirs, versions_file.files_get())

            versions_file.update(file_sums)

        else:
            self.error('Canceled by user.')

def load():
    handler.register(Versions)

