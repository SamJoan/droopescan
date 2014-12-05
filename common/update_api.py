try:
    from bs4 import BeautifulSoup
except:
    pass

from common.functions import version_gt
from common.versions import VersionsFile
import os.path
import requests
import subprocess

GH = 'https://github.com/'
UW = './update-workspace/'

def github_tags_newer(github_repo, versions_file, update_majors):
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

    newer = _newer_tags_get(current_highest, gh_versions)

    return len(newer) > 0

def _newer_tags_get(current_highest, versions):
    """
        Returns versions from versions which are greater than than the highest
            version in each major.
        @param current_highest as returned by VersionsFile.highest_version_major()
        @param versions a list of versions.
    """
    newer = []
    for major in current_highest:
        highest_version = current_highest[major]
        for version in versions:
            if version.startswith(major) and version_gt(version,
                    highest_version):
                newer.append(version)

    return newer

def _github_normalize(github_repo):
    gr = github_repo.strip('/')
    return gr + "/"

def github_repo(github_repo, plugin_name):
    """
        Returns a GitRepo from a github repository after either cloning or
            pulling (depending on whether it exists)
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
    path = None

    def __init__(self, clone_url, plugin_name):
        """
            Base abstraction for working with git repositories.
            @param clone_url the URL to clone the repo from.
            @param plugin_name the current plugin's name (for namespace
                purposes).
        """
        self._clone_url = clone_url
        self.path = '%s%s%s' % (UW, plugin_name + '/', os.path.basename(clone_url[:-1]) + "/")

    def init(self):
        """
            Performs a clone or a pull, depending on whether the repository has
            been previously cloned or not.
        """
        if os.path.isdir(self.path):
            self.pull()
        else:
            self.clone()

    def clone(self):
        """
            Clones a directory based on the clone_url and plugin_name given to
            the constructor. The clone will be located at ./.update-workspace/<plugin_name>/<repo-name>/
        """
        base_dir = '/'.join(self.path.split('/')[:-2])
        try:
            os.makedirs(base_dir, '0700')
        except OSError:
            # Raises an error exception if the leaf directory already exists.
            pass

        self._cmd(['git', 'clone', self._clone_url, self.path])

    def pull(self):
        """
            Performs a pull on this repository.
        """
        self._cmd(['git', 'pull'])

    def tags_newer(self, versions_file):
        """
            Checks this git repo tags for newer versions.
            @param versions_file a common.VersionsFile instance to
                check against.
        """
        pass

    def _cmd(self, *args, **kwargs):

        if 'cwd' not in kwargs:
            kwargs['cwd'] = self.path

        return_code = subprocess.call(*args, **kwargs)
        if return_code != 0:
            command = ' '.join(args)
            raise RuntimeError('Command "%s" failed with exit status "%s"' % (command, return_code))


