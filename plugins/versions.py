
# Not required when not importing versions.
try:
    from bs4 import BeautifulSoup
except:
    pass

from cement.core import handler, controller
from common import VersionsFile, version_gt, md5_file
from plugins.drupal import Drupal
from plugins.silverstripe import SilverStripe
from plugins import HumanBasePlugin
from subprocess import call
from tempfile import NamedTemporaryFile, mkdtemp
from time import sleep
import os
import requests
import shutil
import sys
import tarfile

class VersionGetterBase():
    def newer_get(self, majors):
        """
            get all versions higher than those provided, by major
            @param majors as returned by VersionsFile.latest_by_major
            @return newer {'7': [('7.31', 'http://ftp.drupal.org/files/projects/drupal-7.31.tar.gz')],
                '6': [('6.33', 'http://ftp.drupal.org/files/projects/drupal-6.33.tar.gz')]}
        """
        raise ReferenceError("Parent class should override 'newer_get' method.")

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

class DrupalVersions(VersionGetterBase):

    update_majors = ['6', '7']

    def newer_get(self, majors):
        """
            @see VersionGetterBase.newer_get
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

            assert len(download_links) > 0
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

class SSVersions(VersionGetterBase):
    update_majors = ['3']

    def newer_get(self, majors):
        """
            @see VersionGetterBase.newer_get
        """
        base_url = 'http://www.silverstripe.org/release-archive/'
        resp = requests.get(base_url)
        soup = BeautifulSoup(resp.text)

        download_links = soup.select('.download-releases a.noicon')
        newer = {}
        assert len(download_links) > 0
        for dl_link in download_links:
            if dl_link.text == 'cms.tar.gz':
                url = dl_link.get('href')
                prefix = 'SilverStripe-cms-v'
                v_start = url.index(prefix) + len(prefix)
                v_end = url.index('.tar.gz')

                version = url[v_start:v_end]
                major = version[:version.index('.')]
                is_release_candidate = '-' in version

                if not is_release_candidate:
                    if not major in majors:
                        continue

                    if not version_gt(version, majors[major]):
                        continue

                    if not major in newer:
                        newer[major] = []

                    newer[major].append((version, 'http://www.silverstripe.org'
                        + url))

        return newer


class Versions(HumanBasePlugin):
    class Meta:
        label = 'versions'
        stacked_on = 'base'
        stacked_type = 'nested'
        hide = True

        arguments = [
                (['--cms', '-c'], dict(action='store', required=True,
                    help='Which CMS to generate the XML for', choices=['drupal',
                        'ss'])),
            ]

    @controller.expose(help='', hide=True)
    def default(self):
        # Get the VersionGetter.
        cms = self.app.pargs.cms
        if cms == "drupal":
            vg = DrupalVersions()
            versions_file = versions_file
        elif cms == "ss":
            vg = SSVersions()
            versions_file = SilverStripe.versions_file

        versions = VersionsFile(versions_file)

        ok = self.confirm('This will download a whole bunch of stuff. OK?')
        if ok:
            base_folder = mkdtemp() + "/"

            # Get information needed.
            majors = versions.highest_version_major(vg.update_majors)

            # Download files.
            new = vg.newer_get(majors)
            if len(new) == 0:
                self.error("No new version found, versions.xml is up to date.")

            # Get hashes.
            dl_files = vg.download(new, base_folder)
            extracted_dirs = vg.extract(dl_files, base_folder)
            file_sums = vg.sums_get(extracted_dirs, versions.files_get())

            versions.update(file_sums)
            xml = versions.str_pretty()

            # Final sanity checks.
            f_temp = NamedTemporaryFile(delete=False)
            f_temp.write(xml)
            f_temp.close()
            call(['diff', '-s', f_temp.name, versions_file])
            os.remove(f_temp.name)

            ok = self.confirm('Overwrite %s with the new file?' %
                    versions_file)

            if ok:
                f_real = open(versions_file, 'w')
                f_real.write(xml)
                f_real.close()

                print "Done."

                call(['git', 'status'])
            else:
                self.error('Aborted.')

        else:
            self.error('Aborted.')

def load():
    handler.register(Versions)

