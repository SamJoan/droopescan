try:
    from bs4 import BeautifulSoup
except:
    pass

from common.functions import version_gt
from common.versions import VersionsFile
import requests

GH = 'https://github.com/'

def github_tag_newer(github_repo, versions_file, update_majors):
    """
        Update newer tags based on a github repository.
        @param github_repo the github repository, e.g. 'drupal/drupal'.
        @param versions_file the file path where the versions database can be found.
        @param update_majors major versions to update. If you want to update
            the 6.x and 7.x branch, you would supply a list which would look like
            ['6', '7']
        @return update_needed
    """
    vf = VersionsFile(versions_file)
    current_highest = vf.highest_version_major(update_majors)

    tags_url = '%s%sreleases' % (GH, github_repo)
    resp = requests.get(tags_url)
    bs = BeautifulSoup(resp.text)

    gh_versions = []
    for tag in bs.find_all('span', {'class':'tag-name'}):
        gh_versions.append(tag.text)

    update_needed = False
    for major in current_highest:
        curr_version = current_highest[major]
        for gh_version in gh_versions:
            if gh_version.startswith(major) and version_gt(gh_version,
                    curr_version):
                update_needed = True
                break

    return update_needed






