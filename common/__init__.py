from cement.core import handler
import argparse
import logging
import pystache
import re
import textwrap

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

class SmartFormatter(argparse.RawDescriptionHelpFormatter):
    def _split_lines(self, text, width):
        # this is the RawTextHelpFormatter._split_lines
        if text.startswith('R|'):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)
