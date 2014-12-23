"""
Grabs a list of modules from drupal's online list of modules.
"""

import sys
sys.path.append("../../")

from bs4 import BeautifulSoup
import re
import requests

try:
    what = sys.argv[1]
    total_nb = int(sys.argv[2])
except IndexError:
    print(("Usage: %s (module|theme) total_nb" % sys.argv[0]))
    sys.exit()


per_page = 25
if total_nb % per_page != 0:
    print(("total_nb needs to be a multiple of %s" % per_page))
    sys.exit()

base_url = 'https://drupal.org/project/project_%s?page=%s'
total_pages = total_nb / per_page
module_names = []
for page in range(0, total_pages):
    response = requests.get(base_url % (what, page))
    soup = BeautifulSoup(response.text)

    # find tds with links
    links = soup.select('.node-project-%s > h2 > a' % what)
    assert len(links) == 25, "should have exactly 25 rows every time: page %s, amount %s, items %s" % (page, len(links), links)

    for link in links:
        project_name = link['href'].split("/")[-1]
        print(project_name)
