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
from subprocess import call, check_output
from tempfile import NamedTemporaryFile, mkdtemp
from time import sleep
import os
import requests
import shutil
import sys
import tarfile

def c(*args, **kwargs):
    print args[0]
    return_code = call(*args, **kwargs)
    if return_code != 0:
        raise Exception("Above command failed.")

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
                c(['wget', dl_url, '-O', out_file])
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

    def process_selection(self, versions_string):
        """
            Transforms user input (versions seperated by comma (e.g. 7.23,7.24)
            into what the application expects.
        """
        url = 'http://ftp.drupal.org/files/projects/drupal-%s.tar.gz'
        versions = versions_string.split(",")

        ret = {}
        for version in versions:
            major = str(version).split('.')[0]
            if not major in ret:
                ret[major] = []

            ret[major].append((version, url % version))

        return ret

class SSVersions(VersionGetterBase):
    update_majors = ['3.1', '3.0', '2']

    framework_url = 'https://github.com/silverstripe/silverstripe-framework.git'
    cms_url = 'https://github.com/silverstripe/silverstripe-cms.git'
    #framework_url = '/root/silverstripe-framework/'
    #cms_url = '/root/silverstripe-cms/'

    framework_folder = 'silverstripe-framework/'
    cms_folder = 'silverstripe-cms/'

    def newer_get(self, update_majors):
        """
            @see VersionGetterBase.newer_get
        """

        temp = mkdtemp() + "/"
        c(['git', 'clone', self.framework_url], cwd=temp)
        c(['git', 'clone', self.cms_url], cwd=temp)
        versions = check_output(['git', 'tag'], cwd=temp +
                self.framework_folder).split('\n')

        #{'2': '2.4.8-rc1', '3.0': '3.0.11-rc1', '3.1': '3.1.7-rc1'}

        final = []
        for version in versions:
            major = None
            for m in update_majors:
                if version.startswith(m):
                    major = m

            if major == None:
                print version, "skipped."
                continue

            max_avail = update_majors[major]

            if not version_gt(version, max_avail):
                continue

            final.append(version)

        if len(final) == 0:
            return []
        else:
            return (final, temp)

    def download(self, newer, location):
        versions, temp_dir = newer
        dirs = []
        for ver in versions:
            ver_dir = temp_dir + ver + "/"

            os.mkdir(ver_dir)

            fw_dir = ver_dir + "framework/"
            cms_dir = ver_dir + "cms/"

            c(['cp', '-r', temp_dir + self.framework_folder, fw_dir])
            c(['cp', '-r', temp_dir + self.cms_folder, cms_dir])

            c(['git', 'checkout', '-b', ver, ver],
                    cwd=fw_dir)
            c(['git', 'checkout', '-b', ver, ver],
                    cwd=cms_dir)

            dirs.append((ver, ver_dir))

        return dirs

    def extract(self, files, location):
        return files

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
                (['--selection', '-s'], dict(action='store',
                    help='Comma separated list of versions for drupal_select.'))
            ]

    def download_append(self, vg, versions_file, **additional_params):
        """
            @param vg an instance of VersionGetterBase, such as SSVersions or
                DrupalVersions
            @param versions_file the versions_file which corresponds to this
                VersionGetterBase, in the filesystem.
            @param **aditional_params:
                - override_newer: utilize this value instead of calling
                      newer_get.
        """
        versions = VersionsFile(versions_file)

        base_folder = mkdtemp() + "/"

        # Get information needed.
        if 'override_newer' in additional_params:
            new = additional_params['override_newer']
        else:
            majors = versions.highest_version_major(vg.update_majors)
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

            c(['git', 'status'])
        else:
            self.error('Aborted.')

    @controller.expose(help='', hide=True)
    def default(self):
        # Get the VersionGetter.
        cms = self.app.pargs.cms
        additional_params = {}
        if cms == "drupal":
            vg = DrupalVersions()
            versions_file = Drupal.versions_file

            if self.app.pargs.selection != None:
                additional_params['override_newer'] = vg.process_selection(self.app.pargs.selection)

        elif cms == "ss":
            vg = SSVersions()
            versions_file = SilverStripe.versions_file

        self.download_append(vg, versions_file, **additional_params)

def load():
    handler.register(Versions)

