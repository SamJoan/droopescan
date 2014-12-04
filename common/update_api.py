try:
    from bs4 import BeautifulSoup
except:
    pass

from common.functions import version_gt
from common.versions import VersionsFile
import os.path
import requests

GH = 'https://github.com/'
UW = './update-workspace/'

def github_tag_newer(github_repo, versions_file, update_majors):
    """
        Update newer tags based on a github repository.
        @param github_repo the github repository, e.g. 'drupal/drupal/'.
        @param versions_file the file path where the versions database can be found.
        @param update_majors major versions to update. If you want to update
            the 6.x and 7.x branch, you would supply a list which would look like
            ['6', '7']
        @return update_needed
    """
    github_repo = _github_normalize(github_repo)
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

def _github_normalize(github_repo):
    gr = github_repo.strip('/')
    return gr + "/"

def github_repo(github_repo, plugin_name):
    """
        Returns a GitRepo from a github repository.
        @param github_repo the github repository path, e.g. 'drupal/drupal/'
        @param plugin_name the current plugin's name (for namespace purposes).
    """
    github_repo = _github_normalize(github_repo)
    repo_url = '%s%s' % (GH, github_repo)

    gr = GitRepo(repo_url, plugin_name)
    gr.init()

    return gr

class GitRepo():

    _initialized = False
    _clone_url = None
    _path = None

    def __init__(self, clone_url, plugin_name):
        """
            Base abstraction for working with git repositories.
            @param clone_url the URL to clone the repo from.
            @param plugin_name the current plugin's name (for namespace
                purposes).
        """
        self._clone_url = clone_url
        self._path = '%s%s%s' % (UW, plugin_name + '/', os.path.basename(clone_url[:-1]) + "/")

    def init(self):
        """
            Performs a clone or a pull, depending on whether the repository has
            been previously cloned or not.
        """
        if os.path.isdir(self._path):
            self.pull()
        else:
            self.clone()

    def clone(self):
        base_dir = '/'.join(self._path.split('/')[:-2])
        os.makedirs(base_dir, '0700')

    def pull(self):
        pass

