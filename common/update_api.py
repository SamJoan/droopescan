try:
    from bs4 import BeautifulSoup
except:
    pass

from common.functions import version_gt
from common.versions import VersionsFile
import common.functions
import common.versions
import os
import os.path
import requests
import subprocess

GH = 'https://github.com/'
UW = './.update-workspace/'

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
            version in each major. Note that a major must be in current_highest
            in order for versions of that major branch to appear in the return.
        @param current_highest as returned by VersionsFile.highest_version_major()
        @param versions a list of versions.
        @return a list of versions.
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
            fetching (depending on whether it exists)
        @param github_repo the github repository path, e.g. 'drupal/drupal/'
        @param plugin_name the current plugin's name (for namespace purposes).
    """
    github_repo = _github_normalize(github_repo)
    repo_url = '%s%s' % (GH, github_repo)

    gr = GitRepo(repo_url, plugin_name)
    gr.init()

    return gr

def github_repo_new(repo_url, plugin_name, versions_file, update_majors):
    """
        Convenience method which creates GitRepo and returns the created
        instance, as well as a VersionsFile and tags which need to be updated.
        @param repo_url the github repository path, e.g. 'drupal/drupal/'
        @param plugin_name the current plugin's name (for namespace purposes).
        @param versions_file the path in disk to this plugin's versions.xml
        @param update_majors major versions to update. If you want to update
            the 6.x and 7.x branch, you would supply a list which would look like
            ['6', '7']
        @return (GitRepo, VersionsFile, GitRepo.tags_newer())
    """
    gr = github_repo(repo_url, plugin_name)
    vf = common.versions.VersionsFile(versions_file)
    new_tags = gr.tags_newer(vf, update_majors)

    return gr, vf, new_tags

def hashes_get(versions_file, majors, base_path):
    """
        Gets hashes for currently checked out version.
        @param versions_file a common.VersionsFile instance to
            check against.
        @param majors a list of major branches to check. E.g. ['6', '7']
        @param base_path where to look for files. e.g. './.update-workspace/silverstripe/'
        @return sums {'file1':'hash1'}
    """
    files = versions_file.files_get_all()
    result = {}
    for f in files:
        try:
            result[f] = common.functions.md5_file(base_path + f)
        except IOError:
            # Not all files exist for all versions.
            pass

    return result

class GitRepo():

    _initialized = False
    _clone_url = None
    path = None

    def __init__(self, clone_url, plugin_name):
        """
            Base abstraction for working with git repositories.
            @param clone_url the URL to clone the repo from.
            @param plugin_name used to determine the clone location. The clone
                will be located at ./.update-workspace/<plugin_name>/. Slashes
                are permitted and will create subfolders.
        """
        self._clone_url = clone_url
        self.path = '%s%s/' % (UW, plugin_name)

    def init(self):
        """
            Performs a clone or a fetch, depending on whether the repository has
            been previously cloned or not.
        """
        if os.path.isdir(self.path):
            self.fetch()
        else:
            self.clone()

    def clone(self):
        """
            Clones a directory based on the clone_url and plugin_name given to
            the constructor. The clone will be located at self.path.
        """
        base_dir = '/'.join(self.path.split('/')[:-2])
        try:
            os.makedirs(base_dir, 0o700)
        except OSError:
            # Raises an error exception if the leaf directory already exists.
            pass

        self._cmd(['git', 'clone', self._clone_url, self.path], cwd=os.getcwd())

    def fetch(self):
        """
            Get objects and refs from a remote repository.
        """
        self._cmd(['git', 'fetch', '--all'])

    def tags_newer(self, versions_file, majors):
        """
            Checks this git repo tags for newer versions.
            @param versions_file a common.VersionsFile instance to
                check against.
            @param majors a list of major branches to check. E.g. ['6', '7']
            @raise RuntimeError no newer tags were found.
        """
        highest = versions_file.highest_version_major(majors)
        all = self.tags_get()

        newer = _newer_tags_get(highest, all)

        if len(newer) == 0:
            raise RuntimeError("No new tags found.")

        return newer

    def tags_get(self):
        """
            @return a list with all tags in this repository.
        """
        tags_content = subprocess.check_output(['git', 'tag'], cwd=self.path)
        tags = []
        for line in tags_content.split('\n'):
            tag = line.strip()
            if tag != '':
                tags.append(tag)

        return tags

    def tag_checkout(self, tag):
        """
            Checks out a tag.
            @param tag the tag name.
        """
        self._cmd(['git', 'checkout', tag])

    def hashes_get(self, versions_file, major):
        """
            Gets hashes for currently checked out version.
            @param versions_file a common.VersionsFile instance to
                check against.
            @param majors a list of major branches to check. E.g. ['6', '7']
            @return sums {'file1':'hash1'}
        """
        return hashes_get(versions_file, major, self.path)

    def _cmd(self, *args, **kwargs):
        if 'cwd' not in kwargs:
            kwargs['cwd'] = self.path

        return_code = subprocess.call(*args, **kwargs)
        if return_code != 0:
            command = ' '.join(args[0])
            raise RuntimeError('Command "%s" failed with exit status "%s"' % (command, return_code))

