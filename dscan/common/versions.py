from __future__ import print_function
from dscan.common.functions import version_gt
import dscan
import pystache
import xml.etree.ElementTree as ET

class VersionsFile():
    et = None
    root = None

    changelog_xpath = './files/changelog'

    def __init__(self, xml_file):
        """
        @param xml_file: path to the XML file
        """
        self.et = ET.parse(xml_file)
        self.root = self.et.getroot()

    def files_get(self):
        """
        @return: a list of files which must be used for fingerprinting.
        """
        files = []
        for file in self.root.iter('file'):
            files.append(file.attrib['url'])

        return files

    def files_get_all(self):
        """
        @return: a list of files which includes the changelog.
        """
        files = []
        for file in self.root.iter('file'):
            files.append(file.attrib['url'])

        for file in self.root.iter('changelog'):
            files.append(file.attrib['url'])

        return files

    def changelogs_get(self):
        """
        @return: a list of possible changelogs. More than one may be returned
            in cases where the location of the changelog varies between major
            versions of a CMS.
        """
        changelogs_elem = self.root.findall(self.changelog_xpath)
        changelogs = []
        for c in changelogs_elem:
            changelogs.append(c.attrib['url'])

        return changelogs

    def changelog_identify(self, ch_hash):
        changelog_files = self.root.findall(self.changelog_xpath + '/version')
        for version in changelog_files:
            hsh = version.attrib['md5']
            nb = version.attrib['nb']
            if hsh == ch_hash:
                return nb

        return False

    def files_per_version(self):
        xpath = './files/file'
        files = self.root.findall(xpath)

        versions = {}
        for file in files:
            vfile = file.findall('version')
            for version in vfile:
                nb = version.attrib['nb']
                if not nb in versions:
                    versions[nb] = []

                versions[nb].append(file.attrib['url'])

        return versions

    def files_per_version_major(self, major_numbers):
        """
        @param major_numbers: numbers which mean a major. In drupal 7.x is
            the major seven, so input 1. In SS, 3.1 is the major (two numbers),
            os input two.
        """
        fpv = self.files_per_version()
        majors = {}
        for version in fpv:
            major = ".".join(version.split(".")[0:major_numbers])

            if not major in majors:
                majors[major] = {}

            majors[major][version] = fpv[version]

        return majors

    def version_get(self, url_hash):
        matches = {}
        for url in url_hash:
            actual_hash = url_hash[url]

            xpath = "./files/file[@url='%s']/version"
            versions = self.root.findall(xpath % url)

            for version in versions:
                if version.attrib['md5'] == actual_hash:
                    version_nb = version.attrib['nb']
                    if not version_nb in matches:
                        matches[version_nb] = 1
                    else:
                        matches[version_nb] += 1

        if len(matches) == 0:
            return []

        # version = max(matches.iterkeys(), key=(lambda key: matches[key]))
        # Get highest match number.
        highest_nb = 0
        for match in matches:
            nb_similar = matches[match]
            if nb_similar > highest_nb:
                highest_nb = nb_similar

        # Get those who have the highest match number.
        final_matches = []
        for match in matches:
            nb_similar = matches[match]
            if nb_similar == highest_nb:
                final_matches.append(match)

        return sorted(final_matches)

    def highest_version(self):
        """
            @return: the highest version number in the XML file.
        """
        xpath = './files/file/version'
        versions = self.root.findall(xpath)
        highest = 0
        for version_elem in versions:
            version = version_elem.attrib['nb']
            if self.version_gt(version, highest):
                highest = version

        return highest

    def version_gt(self, version, gt):
        return version_gt(version, gt)

    def highest_version_major(self, majors_include):
        """
        @param majors_include: a list of majors. Returns only majors
            that are included in that list.
        @return: highest version per major release.
            e.g. {'7': '7.28', '6': '6.15'}
            If a major in majors_include is not present in the XML file, it
            returns a version which is lesser to all versions in that major.
            E.g. 8.0 -> 7.9999
        """
        xpath = './files/file/version'
        versions = self.root.findall(xpath)
        highest = {}
        for version_elem in versions:
            version = version_elem.attrib['nb']

            major = None
            for possibility in majors_include:
                if version.startswith(possibility):
                    major = possibility

            if major not in highest:
                highest[major] = version

            if self.version_gt(version, highest[major]):
                highest[major] = version

        majors = {}
        for key in majors_include:
            in_xml_file = key in highest
            if in_xml_file:
                majors[key] = highest[key]
            else:
                splat = str(key).split('.')
                last_digit = len(splat) - 1
                splat[last_digit] = str(int(splat[last_digit]) - 1)
                majors[key] = ".".join(splat) + ".9999"

        return majors

    def version_exists(self, file, check_version, expected_hash):
        """
        @param file: a file element (ElementTree element)
        @param check_version: version to check for.
        @param expected_hash: the hash that the file should have if it is
            present.
        @return: True if version is present within a file element, False if
        it is not.
        @raise RuntimeError: If element exists but has a different hash than the
        one expected.
        """
        versions = file.findall('./version')
        for version in versions:
            nb = version.attrib['nb']
            hsh = version.attrib['md5']

            if nb == check_version:
                if hsh == expected_hash:
                    return True

        return False

    def update(self, sums):
        """
        Update self.et with the sums as returned by VersionsX.sums_get
        @param sums: {'version': {'file1':'hash1'}}
        """
        for version in sums:
            hashes = sums[version]
            for filename in hashes:
                hsh = hashes[filename]
                file_xpath = './files/*[@url="%s"]' % filename
                try:
                    file_add = self.root.findall(file_xpath)[0]
                except IndexError:
                    raise ValueError("Attempted to update element '%s' which doesn't exist" % filename)

                # Do not add duplicate, equal hashes.
                if not self.version_exists(file_add, version, hsh):
                    new_ver = ET.SubElement(file_add, 'version')
                    new_ver.attrib = {
                            'md5': hsh,
                            'nb': version
                    }

    def indent(self, elem, level=0):
        # @see http://effbot.org/zone/element-lib.htm#prettyprint
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent(elem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def str_pretty(self):
        self.indent(self.root)
        return ET.tostring(self.root, encoding='utf-8')

    def has_changelog(self):
        changelogs = self.root.findall(self.changelog_xpath)

        return len(changelogs) > 0

    def has_hash(self, hash):
        file_xpath = './/version[@md5="%s"]' % hash
        return self.et.find(file_xpath) != None

