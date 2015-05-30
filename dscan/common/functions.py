from __future__ import print_function
from common.enum import colors, ScanningMethod
import hashlib
import pystache
import re
import xml.etree.ElementTree as ET

def repair_url(url, out):
    """
        Fixes URL.
        @param url: url to repair.
        @param out: instance of StandardOutput as defined in this lib.
        @return: Newline characters are stripped from the URL string.
            If the url string parameter does not start with http, it prepends http://
            If the url string parameter does not end with a slash, appends a slash.
    """
    if not url:
        out.fatal("--url parameter is blank.")

    url = url.strip('\n')
    if not re.match(r"^http", url):
        url = "http://" + url

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
    @param url: the url to get the base of.
    @return: the protocol, domain and port of a URL, concatenated. If the
        URL is relative, False is returned.
    """

    if 'http' not in url:
        return False

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

def strip_whitespace(s):
    return re.sub(r'\s+', ' ', s)

def is_string(var):
    return isinstance(var, str)

def dict_combine(x, y):
    z = x.copy()
    z.update(y)
    return z

def file_len(fname):
    i = 0
    with open(fname) as f:
        for l in f:
            i += 1

    return i

def strip_letters(string):
    return ''.join([c for c in str(string) if c in '1234567890.-'])

def version_gt(version, gt):
    """
        Code for parsing simple, numeric versions. Letters will be stripped
        prior to comparison. Simple appendages such as 1-rc1 are supported.
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

            v = version_split[i]
            g = gt_split[i]

            v_is_rc = '-' in v
            g_is_rc = '-' in g

            if v_is_rc:
                v_split = v.split('-')
                v = v_split[0]
                v_rc_nb = int(''.join(v_split[1:]))

            if g_is_rc:
                g_split = g.split('-')
                g = g_split[0]
                g_rc_nb = int(''.join(g_split[1:]))

            v = int(v)
            g = int(g)

            if v > g:
                gt = True
                break
            elif v < g:
                break
            else:
                if not v_is_rc and g_is_rc:
                    gt = True
                    break
                elif v_is_rc and not g_is_rc:
                    break
                elif v_is_rc and g_is_rc:
                    if v_rc_nb > g_rc_nb:
                        gt = True
                        break
                    elif v_rc_nb < g_rc_nb:
                        break

        else:
            nb = longest[i]

            is_rc = '-' in nb
            if is_rc:
                nb = nb.split('-')[0]

            if int(nb) > 0:
                if longest == version_split:
                    gt = True
                    break
                else:
                    break

    return gt

def md5_file(filename):
    return hashlib.md5(open(filename).read()).hexdigest()

def version_get():
    """
        Returns current droopescan version. Not. It was broken and not a useful
        feature, so I replaced it with a fake version.
    """
    version = '1.33.7'
    return version

def error(msg):
    raise RuntimeError('\033[91m%s\033[0m' % msg)

