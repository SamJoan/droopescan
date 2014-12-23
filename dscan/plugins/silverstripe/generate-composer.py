"""
Grabs a list of modules from SilverStripe's online list of modules.
"""

import sys
sys.path.append("../../")

from bs4 import BeautifulSoup
import re
import requests

try:
    what = sys.argv[1]
except IndexError:
    print("Generates ONLY the module names to import from composer. See notes \
        for getting modules")
    print(("Usage: %s (all|theme)" % sys.argv[0]))
    sys.exit()

what = "" if what == "all" else what

# SS displays 16 modules per page :P
per_page = 16
base_url = 'http://addons.silverstripe.org/add-ons?search=&type=%s&sort=downloads&start=%s'
module_names = []
for page in range(0, 1000):
    start = page * per_page
    response = requests.get(base_url % (what, start))
    soup = BeautifulSoup(response.text)

    links = soup.select('.table-addons td:first-child a')

    if len(links) < per_page:
        if len(links) == 0:
            break
        else:
            pass

    for link in links:
        print(link.contents[0])
