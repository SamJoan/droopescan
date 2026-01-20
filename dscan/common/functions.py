from __future__ import print_function
from collections import OrderedDict
from dscan.common.enum import colors, ScanningMethod
try:
    from requests.exceptions import ConnectionError, ReadTimeout, ConnectTimeout, \
            TooManyRedirects
except:
    old_req = """Running a very old version of requests! Please `pip
        install -U requests`."""
    print(old_req)

import dscan
import hashlib
import pystache
import re
import sys
import traceback
import xml.etree.ElementTree as ET

SPLIT_PATTERN = re.compile('[ \t]+')

def repair_url(url):
    """
    Fixes URL.
    @param url: url to repair.
    @param out: instance of StandardOutput as defined in this lib.
    @return: Newline characters are stripped from the URL string.
        If the url string parameter does not start with http, it prepends http://
        If the url string parameter does not end with a slash, appends a slash.
        If the url contains a query string, it gets removed.
    """
    url = url.strip('\n')
    if not re.match(r"^http", url):
        url = "http://" + url

    if "?" in url:
        url, _ = url.split('?')

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
    f = open(dscan.PWD + 'common/template/' + template_file, 'r')
    template = f.read()

    renderer = pystache.Renderer(search_dirs=dscan.PWD)
    return renderer.render(template, variables)

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
        for _ in f:
            i += 1

    return i

def strip_letters(string):
    return ''.join([c for c in str(string) if c in '1234567890.-_'])

def version_gt(version, gt):
    """
    Code for parsing simple, numeric versions. Letters will be stripped prior to
    comparison. Simple appendages such as 1-rc1 are supported. Test cases for
    function are present on dscan/tests/fingerprint_tests.py
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

    gt = False
    for i in range(l):
        overcame_shortest = i >= shortest_len

        if not overcame_shortest:

            v = version_split[i]
            g = gt_split[i]

            v_is_rc = '-' in v or '_' in v
            g_is_rc = '-' in g or '_' in g

            if v_is_rc:
                v_split = re.split(r'[-_]', v)
                v = v_split[0]
                try:
                    v_rc_nb = int(''.join(v_split[1:]))
                except ValueError:
                    v_rc_nb = 0

            if g_is_rc:
                g_split = re.split(r'[-_]', g)
                g = g_split[0]
                try:
                    g_rc_nb = int(''.join(g_split[1:]))
                except ValueError:
                    g_rc_nb = 0

            try:
                v = int(v)
            except ValueError:
                v = 0

            try:
                g = int(g)
            except ValueError:
                g = 0

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

            is_rc = '-' in nb or '_' in nb
            if is_rc:
                nb = re.split(r'[-_]', nb)[0]

            try:
                nb_int = int(nb)
            except ValueError:
                if longest == version_split:
                    break
                else:
                    gt = True
                    break

            if nb_int > 0:
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
    feature, so I replaced it with a way more elite version.
    """
    version = '1.46.0'
    return version

def error(msg):
    raise RuntimeError('\033[91m%s\033[0m' % msg)

def exc_handle(url, out, testing):
    """
    Handle exception. If of a determinate subset, it is stored into a file as a
    single type. Otherwise, full stack is stored. Furthermore, if testing, stack
    is always shown.
    @param url: url which was being scanned when exception was thrown.
    @param out: Output object, usually self.out.
    @param testing: whether we are currently running unit tests.
    """
    quiet_exceptions = [ConnectionError, ReadTimeout, ConnectTimeout,
            TooManyRedirects]
    type, value, _ = sys.exc_info()
    if type not in quiet_exceptions or testing:
        exc = traceback.format_exc()
        exc_string = ("Line '%s' raised:\n" % url) + exc
        out.warn(exc_string, whitespace_strp=False)

        if testing:
            print(exc)
    else:
        exc_string = "Line %s '%s: %s'" % (url, type, value)
        out.warn(exc_string)

def tail(f, window=20):
    """
    Returns the last `window` lines of file `f` as a list.
    @param window: the number of lines.
    """
    if window == 0:
        return []
    BUFSIZ = 1024
    f.seek(0, 2)
    bytes = f.tell()
    size = window + 1
    block = -1
    data = []
    while size > 0 and bytes > 0:
        if bytes - BUFSIZ > 0:
            # Seek back one whole BUFSIZ
            f.seek(block * BUFSIZ, 2)
            # read BUFFER
            data.insert(0, f.read(BUFSIZ).decode('utf-8', errors='ignore'))
        else:
            # file too small, start from begining
            f.seek(0,0)
            # only read what was not read
            data.insert(0, f.read(bytes).decode('utf-8', errors='ignore'))

        linesFound = data[0].count('\n')
        size -= linesFound
        bytes -= BUFSIZ
        block -= 1
    return ''.join(data).splitlines()[-window:]

def _line_contains_host(url):
    return re.search(SPLIT_PATTERN, url)

def process_host_line(line):
    """
    Processes a line and determines whether it is a tab-delimited CSV of
    url and host.

    Strips all strings.

    @param line: the line to analyse.
    @param opts: the options dictionary to modify.
    @return: a tuple containing url, and host header if any change is
        required. Otherwise, line, null is returned.
    """
    if not line:
        return None, None

    host = None
    if _line_contains_host(line):
        url, host = re.split(SPLIT_PATTERN, line.strip())
    else:
        url = line.strip()

    return url, host

def instances_get(opts, plugins, url_file_input, out):
    """
    Creates and returns an ordered dictionary containing instances for all available
    scanning plugins, sort of ordered by popularity.
    @param opts: options as returned by self._options.
    @param plugins: plugins as returned by plugins_util.plugins_base_get.
    @param url_file_input: boolean value which indicates whether we are
        scanning an individual URL or a file. This is used to determine
        kwargs required.
    @param out: self.out
    """
    instances = OrderedDict()
    preferred_order = ['wordpress', 'joomla', 'drupal']

    for cms_name in preferred_order:
        for plugin in plugins:
            plugin_name = plugin.__name__.lower()

            if cms_name == plugin_name:
                instances[plugin_name] = instance_get(plugin, opts,
                        url_file_input, out)

    for plugin in plugins:
        plugin_name = plugin.__name__.lower()
        if plugin_name not in preferred_order:
            instances[plugin_name] = instance_get(plugin, opts,
                    url_file_input, out)

    return instances

def instance_get(plugin, opts, url_file_input, out):
    """
    Return an instance dictionary for an individual plugin.
    @see Scan._instances_get.
    """
    inst = plugin()
    hp, func, enabled_func = inst._general_init(opts, out)
    name = inst._meta.label

    kwargs = {
        'hide_progressbar': hp,
        'functionality': func,
        'enabled_functionality': enabled_func
    }

    if url_file_input:
        del kwargs['hide_progressbar']

    return {
        'inst': inst,
        'kwargs': kwargs
    }

def result_anything_found(result):
    """
    Interim solution for the fact that sometimes determine_scanning_method can
    legitimately return a valid scanning method, but it results that the site
    does not belong to a particular CMS.
    @param result: the result as passed to Output.result()
    @return: whether anything was found.
    """
    keys = ['version', 'themes', 'plugins', 'interesting urls']
    anything_found = False
    for k in keys:
        if k not in result:
            continue
        else:
            if not result[k]['is_empty']:
                anything_found = True

    return anything_found

