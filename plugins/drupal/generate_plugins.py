"""
Grabs a list of modules from drupal's online list of modules.
"""

import sys
sys.path.append("../../")

from bs4 import BeautifulSoup
import re
import requests

try:
    total_nb = int(sys.argv[1])
except IndexError:
    print("Usage: %s total_nb" % sys.argv[0])
    sys.exit()

if total_nb % 100 != 0:
    print("total_nb needs to be a multiple of 100")
    sys.exit()

base_url = 'https://drupal.org/project/usage?page=%s'
total_pages = total_nb / 100
module_names = []
for page in xrange(0,total_pages + 1):
    response = requests.get(base_url % page)
    soup = BeautifulSoup(response.text)

    # find tds with links
    rows = soup.find_all('td')
    links = []
    for row in rows:
        links += row.find_all('a')

    for link in links:
        splat = link["href"].split("/")
        module_names += splat[-1:]

    if page == 0:
        module_names.remove("drupal")

for module in module_names[:total_nb]:
    print module

