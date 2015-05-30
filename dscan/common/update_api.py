from __future__ import print_function
try:
    from bs4 import BeautifulSoup
except:
    pass

from common.functions import version_gt
from common.versions import VersionsFile
from datetime import datetime, timedelta
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
    @param github_repo: the github repository, e.g. 'drupal/drupal/'.
    @param versions_file: the file path where the versions database can be found.
    @param update_majors: major versions to update. If you want to update
        the 6.x and 7.x branch, you would supply a list which would look like
        ['6', '7']
    @return: a boolean value indicating whether an update is needed
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
    @param current_highest: as returned by VersionsFile.highest_version_major()
    @param versions: a list of versions.
    @return: a list of versions.
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
    Returns a GitRepo from a github repository after either cloning or fetching
    (depending on whether it exists)
    @param github_repo: the github repository path, e.g. 'drupal/drupal/'
    @param plugin_name: the current plugin's name (for namespace purposes).
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
    @param repo_url: the github repository path, e.g. 'drupal/drupal/'
    @param plugin_name: the current plugin's name (for namespace purposes).
    @param versions_file: the path in disk to this plugin's versions.xml
    @param update_majors: major versions to update. If you want to update
        the 6.x and 7.x branch, you would supply a list which would look like
        ['6', '7']
    @return: a tuple containing (GitRepo, VersionsFile, GitRepo.tags_newer())
    """
    gr = github_repo(repo_url, plugin_name)
    vf = common.versions.VersionsFile(versions_file)
    new_tags = gr.tags_newer(vf, update_majors)

    return gr, vf, new_tags

def hashes_get(versions_file, base_path):
    """
    Gets hashes for currently checked out version.
    @param versions_file: a common.VersionsFile instance to check against.
    @param base_path: where to look for files. e.g. './.update-workspace/silverstripe/'
    @return: checksums {'file1': 'hash1'}
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

def file_mtime(file_path):
    """
    Returns the file modified time. This is with regards to the last
    modification the file has had in the droopescan repo, rather than actual
    file modification time in the filesystem.
    @param file_path: file path relative to the executable.
    @return datetime.datetime object.
    """
    if not os.path.isfile(file_path):
        raise IOError('File "%s" does not exist.' % file_path)

    ut = subprocess.check_output(['git', 'log', '-1', '--format=%ct',
        file_path]).strip()

    return datetime.fromtimestamp(int(ut))

class PT():
    """
    Pagination types.

    Normal represents normal pagination, starts at page 0 and then 1, 2, 3
    and so on.

    Skip pagination represents paginations that require you to tell them how
    many elements to skip. They start at 0, and then 10, 20, 30 and so on,
    incrementing in per_page increments.
    """
    normal = 0
    skip = 1

def modules_get(url_tpl, per_page, css, max_modules=2000, pagination_type=PT.normal):
    """
    Gets a list of modules. Note that this function can also be used to get
    themes.
    @param url_tpl: a string such as
    https://drupal.org/project/project_module?page=%s. %s will be replaced with
    the page number.
    @param per_page: how many items there are per page.
    @param css: the elements matched by this selector will be returned by the
        iterator.
    @param max_modules: absolute maximum modules we will attempt to request.
    @param pagination_type: type of pagination. See the PaginationType enum
        for more information.
    @return: bs4.element.Tag
    @see: http://www.crummy.com/software/BeautifulSoup/bs4/doc/#css-selectors
    @see: http://www.crummy.com/software/BeautifulSoup/bs4/doc/#tag
    """
    page = 0
    elements = False
    done_so_far = 0

    max_potential_pages = max_modules / per_page
    print("Maximum pages: %s." % max_potential_pages)

    stop = False
    while elements == False or len(elements) == per_page:
        url = url_tpl % page

        r = requests.get(url)
        bs = BeautifulSoup(r.text)
        elements = bs.select(css)

        for element in elements:
            yield element
            done_so_far += 1

            if done_so_far >= max_modules:
                stop = True
                break


        if stop:
            break

        if pagination_type == PT.normal:
            print('Finished parsing page %s.' % page)
            page += 1
        elif pagination_type == PT.skip:
            print('Finished parsing page %s.' % (page / per_page))
            page += per_page
        else:
            assert False

def update_modules_check(plugin):
    """
    @param plugin: plugin to check.
    @return: True if modules need to be updated.
    """
    today = datetime.today()
    mtime = file_mtime(plugin.plugins_file)
    delta = today - mtime

    return delta > timedelta(days=365)

class GitRepo():
    """
    Base abstraction for working with git repositories.
    """

    _initialized = False
    _clone_url = None
    path = None

    def __init__(self, clone_url, plugin_name):
        """
        Default constructor.
        @param clone_url: the URL to clone the repo from.
        @param plugin_name: used to determine the clone location. The clone
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
        Clones a directory based on the clone_url and plugin_name given to the
        constructor. The clone will be located at self.path.
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
        @param versions_file: a common.VersionsFile instance to
            check against.
        @param majors: a list of major branches to check. E.g. ['6', '7']
        @raise RuntimeError: no newer tags were found.
        """
        highest = versions_file.highest_version_major(majors)
        all = self.tags_get()

        newer = _newer_tags_get(highest, all)

        if len(newer) == 0:
            raise RuntimeError("No new tags found.")

        return newer

    def tags_get(self):
        """
        @return: a list with all tags in this repository.
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
        @param tag: the tag name.
        """
        self._cmd(['git', 'checkout', tag])

    def hashes_get(self, versions_file, major):
        """
        Gets hashes for currently checked out version.
        @param versions_file: a common.VersionsFile instance to
            check against.
        @return: sums {'file1':'hash1'}
        """
        return hashes_get(versions_file, self.path)

    def _cmd(self, *args, **kwargs):
        if 'cwd' not in kwargs:
            kwargs['cwd'] = self.path

        return_code = subprocess.call(*args, **kwargs)
        if return_code != 0:
            command = ' '.join(args[0])
            raise RuntimeError('Command "%s" failed with exit status "%s"' % (command, return_code))


