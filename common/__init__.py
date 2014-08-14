from cement.core import handler
import argparse
import logging
import pystache
import re
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

class Verb():
    head = 'head'
    get = 'get'

def validate_url(url):
    if not re.match(r"^http", url):
        fatal("--url parameter invalid.")

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

def echo(msg):
    print(msg)

def warn(msg):
    print textwrap.fill(colors['warn'] + "[+] " + msg + colors['endc'], 79)

def fatal(msg):
    msg = textwrap.fill(colors['red'] + "[+] " + msg + colors['endc'], 79)
    raise RuntimeError(msg)

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

class VersionsFile():
    et = None
    root = None
    def __init__(self, xml_file):
        self.et = ET.parse(xml_file)
        self.root = self.et.getroot()

    def files_get(self):
        files = []
        for file in self.root.iter('file'):
            files.append(file.attrib['url'])

        return files

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

        version = max(matches.iterkeys(), key=(lambda key: matches[key]))
        return [version]

    def highest_version(self):
        '''
            Returns the highest version number in the XML file.
        '''
        xpath = './files/file/version'
        versions = self.root.findall(xpath)
        highest = 0
        for version_elem in versions:
            version = version_elem.attrib['nb']
            if version > highest:
                highest = version

        return highest

    def _strip_letters(self, string):
        return ''.join([c for c in string if c in '1234567890.'])

    def version_gt(self, version, gt):
        """
            Fuck parsing versions, man.
        """
        version_split = self._strip_letters(version).split('.')
        gt_split = self._strip_letters(gt).split('.')

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
                elif g < v:
                    break
            else:
                if int(longest[i]) > 0:
                    if longest == version_split:
                        gt = True
                        break
                    else:
                        break

        return gt

    def highest_version_major(self):
        """
        returns highest version per major release
        """
        xpath = './files/file/version'
        versions = self.root.findall(xpath)
        highest = {}
        for version_elem in versions:
            version = version_elem.attrib['nb']
            major = version.split('.')[0]

            if major not in highest:
                highest[major] = version

            if version > highest[major]:
                highest[major] = version

        return highest

class SmartFormatter(argparse.RawDescriptionHelpFormatter):
    def _split_lines(self, text, width):
        # this is the RawTextHelpFormatter._split_lines
        if text.startswith('R|'):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)
