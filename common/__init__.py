from cement.core import handler
import droopescan
import pystache
import re

def validate_url(url):
    if not url:
        raise RuntimeError("--url was not specified.")

    if not re.match(r"^http", url):
        raise RuntimeError("--url parameter invalid.")

def validate_enumerate(enumerate, valid_enumerate):
    if not enumerate in valid_enumerate:
        raise RuntimeError("Invalid --enumerate. Valid options are %s"
                % valid_enumerate)

def validate_method(method, method_enum):
    if not in_enum(method, method_enum):
        raise RuntimeError("Invalid --method. Valid options are %s" %
                enum_list(method_enum))
    else:
        return getattr(method_enum, method)

def in_enum(string, enum):
    return string in enum.__dict__

def enum_list(enum):
    methods = []
    for method in enum.__dict__:
        if not method.startswith("_"):
            methods.append(method)

    return methods

def template(template_file, variables):
    f = open(template_file, "r")
    template = f.read()

    return pystache.render(template, variables)

def echo(msg, padding = "[+] "):
    print("%s%s" % (padding, msg))
