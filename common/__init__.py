from cement.core import handler
import droopescan
import re

def url_validate(url):
    if not url:
        raise RuntimeError("--url was not specified.")

    if not re.match(r"^http", url):
        raise RuntimeError("--url parameter invalid.")

def enumerate_validate(enumerate, valid_enumerate):
    if not enumerate in valid_enumerate:
        raise RuntimeError("Invalid --enumerate. Valid options are %s"
                % valid_enumerate)
