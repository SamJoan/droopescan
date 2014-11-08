from __future__ import print_function
from cement.core import handler
import argparse
import hashlib
import json
import logging
import pystache
import re
import sys
import textwrap
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.WARN)
logger = logging.getLogger(__name__)

colors = {
        'warn': '\033[93m',
        'green': '\033[92m',
        'header': '\033[95m',
        'blue': '\033[94m',
        'red': '\033[91m',
        'endc': '\033[0m',
    }

class Enumerate():
    a = 'a'
    t = 't'
    p = 'p'
    v = 'v'
    i = 'i'

class ScanningMethod():
    not_found = 'not_found'
    forbidden = 'forbidden'
    ok = 'ok'

class ValidOutputs():
    standard = 'standard'
    json = 'json'

class Verb():
    head = 'head'
    get = 'get'

def validate_url(url, out):
    """
        Checks if a URL is valid and calls fatal() if not. It also returns a
        patched-up version of URL, with e.g. an ending slash, if it didn't have
        one.
        @param url url to check
        @param out instance of StandardOutput as defined in this lib.
    """
    if not url:
        out.fatal("--url parameter is required.")

    url = url.strip('\n')

    if not re.match(r"^http", url):
        out.fatal("--url parameter invalid.")

    # add '/' to urls which do not end with '/' already.
    if not url.endswith("/"):
        return url + "/"
    else :
        return url

def in_enum(string, enum):
    return string in enum.__dict__

def enum_list(enum):
    methods = []
    for method in enum.__dict__:
        if not method.startswith("_"):
            methods.append(method)

    return methods

def base_url(url):
    """
        Returns the protocol, domain and port of a URL.
    """
    url_split = url.split("/")
    return url_split[0] + "//" + url_split[2] + "/"

def scan_http_status(scanning_method):
    if scanning_method == ScanningMethod.not_found:
        return 404
    elif scanning_method == ScanningMethod.forbidden:
       return 403
    elif scanning_method == ScanningMethod.ok:
        return 200

    raise RuntimeError("Unexpected argument to common.scan_method")

def template(template_file, variables={}):
    variables.update(colors)
    f = open('common/template/' + template_file, 'r')
    template = f.read()

    return pystache.render(template, variables)

class StandardOutput():

    errors_display = True
    error_log_file = None
    error_log = None

    def __init__(self, error_log='-'):
        self.error_log_file = error_log
        if error_log == '-':
            self.error_log = sys.stderr
        else:
            self.errors_display = True
            self.error_log = open(error_log, 'w')

    def __del__(self):
        if self.error_log_file != '-':
            self.error_log.close()

    def echo(self, msg):
        """
            For miscelaneous messages. E.g. "Initializing scanning".
        """
        print(msg)

    def result(self, result, functionality):
        """
            For the final result of the scan.
            @param result as returned by BasePluginInternal.url_scan
        """
        for enumerate in result:

            # The host is a special header, we must not attempt to display it.
            if enumerate == "host":
                continue

            result_ind = result[enumerate]
            finds = result_ind['finds']
            is_empty = result_ind['is_empty']

            template_str = functionality[enumerate]['template']
            template_params = {
                    'noun': enumerate,
                    'Noun': enumerate.capitalize(),
                    'items': finds,
                    'empty': is_empty,
                }

            self.echo(template(template_str, template_params))

    def warn(self, msg):
        """
            For things that have gone seriously wrong but don't merit a program
            halt.
            Outputs to stderr, so JsonOutput does not need to override.
        """
        if self.errors_display:
            print(textwrap.fill(colors['warn'] + "[+] " + msg + colors['endc'], 79),
                    file=self.error_log)

    def fatal(self, msg):
        """
            For errors so grave that the program cannot continue.
        """
        msg = textwrap.fill(colors['red'] + "[+] " + msg + colors['endc'], 79)
        raise RuntimeError(msg)

class JsonOutput(StandardOutput):

    errors_display = False

    def echo(self, msg):
        pass

    def result(self, result, functionality=None):
        print(json.dumps(result))

def is_string(var):
    return isinstance(var, basestring)

def dict_combine(x, y):
    z = x.copy()
    z.update(y)
    return z

def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

def strip_letters(string):
    return ''.join([c for c in str(string) if c in '1234567890.'])

def version_gt(version, gt):
    """
        Code for parsing simple, numeric versions. Letters will be stripped
        prior to comparison.
    """
    version_split = strip_letters(version).split('.')
    gt_split = strip_letters(gt).split('.')

    v_len = len(version_split)
    g_len = len(gt_split)
    if v_len > g_len:
        longest = version_split
        shortest_len = len(gt_split)
        l = v_len
    else:
        longest = gt_split
        shortest_len = len(version_split)
        l = g_len

    # in case of equality, return False
    gt = False
    for i in range(l):
        overcame_shortest = i >= shortest_len

        if not overcame_shortest:
            v = int(version_split[i])
            g = int(gt_split[i])
            if v > g:
                gt = True
                break
            elif v < g:
                break
        else:
            if int(longest[i]) > 0:
                if longest == version_split:
                    gt = True
                    break
                else:
                    break

    return gt

def md5_file(filename):
    return hashlib.md5(open(filename).read()).hexdigest()

class VersionsFile():
    et = None
    root = None

    changelog_xpath = './files/changelog'

    def __init__(self, xml_file):
        self.et = ET.parse(xml_file)
        self.root = self.et.getroot()

    def files_get(self):
        files = []
        for file in self.root.iter('file'):
            files.append(file.attrib['url'])

        return files

    def changelog_get(self):
        changelog = self.root.find(self.changelog_xpath)
        return changelog.attrib['url']

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

    def files_per_version_major(self):
        fpv = self.files_per_version()
        majors = {}
        for version in fpv:
            major = version.split(".")[0]
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
        '''
            Returns the highest version number in the XML file.
        '''
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
            Returns highest version per major release.
            @majors_include a list of majors. if present, returns only majors
                that are included in that list
        """
        xpath = './files/file/version'
        versions = self.root.findall(xpath)
        highest = {}
        for version_elem in versions:
            version = version_elem.attrib['nb']

            for possibility in majors_include:
                if version.startswith(possibility):
                    major = possibility

            if major not in highest:
                highest[major] = version

            if self.version_gt(version, highest[major]):
                highest[major] = version

        majors = {}
        for key in majors_include:
            try:
                majors[key] = highest[key]
            except KeyError:
                majors[key] = key + ".0"

        return majors

    def version_exists(self, file, check_version, expected_hash):
        """
            Returns True if version is present within a file element, False if
            it is not.
            @param file a file element (ElementTree element)
            @param check_version version to check for.
            @param expected_hash the hash that the file should have if it is
                present.
            @raises If element exists but has a different hash than the one
                expected, it raises a RuntimeError.
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
        """
        for version in sums:
            hashes = sums[version]
            for filename in hashes:
                hsh = hashes[filename]
                file_xpath = './files/file[@url="%s"]' % filename
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

class SmartFormatter(argparse.RawDescriptionHelpFormatter):
    def _split_lines(self, text, width):
        # this is the RawTextHelpFormatter._split_lines
        if text.startswith('R|'):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)

class ProgressBar():
    def __init__(self, stream):
        self.stream = stream

    def set(self, items_processed, items_total, barLen = 50):
        items_processed = int(items_processed)
        items_total = int(items_total)
        percent = (items_processed * 100) / items_total
        self.stream.write("\r")

        real_percent = percent / 2
        progress = ""
        for i in range(barLen):
            if i < real_percent:
                progress += "="
            else:
                progress += " "

        self.stream.write("[ %s ] %d/%d (%d%%)" % (progress, items_processed, items_total, percent))
        self.stream.flush()

    def hide(self):
        self.stream.write("\r")
        self.stream.write(" " * 80)
        self.stream.write("\r")
