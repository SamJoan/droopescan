"""
Convert composer package name to actual folder name.

This is not very simple, it is done by a request to
https://packagist.org/p/{package-name}.json, see notes
"""

import sys, os
sys.path.append("../../")

import requests
from pprint import pprint

try:
    composer_file = sys.argv[1]
except IndexError:
    print("Usage: %s FILE_WITH_COMPOSER_MODULES" % sys.argv[0])
    sys.exit()

f = open(composer_file)

url = 'https://packagist.org/p/%s.json'

for line in f:
    module_name = line.strip()
    r = requests.get(url % module_name)
    response = r.json()

    try:
        for package_name in response['packages']:
            versions = response['packages'][package_name]
            folder_name = None
            for v in versions:
                version = versions[v]
                try:
                    folder_name = version["extra"]["installer-name"]
                    break
                except KeyError:
                    #print "Didnt find installer-name, that is OK"
                    pass
    except KeyError:
        if 'not found' in r.text:
            # go w/ the default name.
            pass
        else:
            # god knows whatever the fuck happened there.
            print module_name
            pprint(response)
            raise

    if not folder_name:
        folder_name = os.path.basename(module_name)

    print folder_name

