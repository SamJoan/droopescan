from __future__ import print_function
from cement.core import handler, controller
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
from dscan.common.exceptions import FileEmptyException, CannotResumeException
from dscan.common.http import BlockAll
from dscan.common import ScanningMethod, StandardOutput, JsonOutput, \
    VersionsFile, RequestsLogger
from dscan.common import template, enum_list, dict_combine, base_url, file_len
from dscan.common.output import ProgressBar
from dscan import common
from functools import partial
from os.path import dirname
from requests import Session
import dscan
import dscan.common.functions as f
import hashlib
import os
import re
import requests
import sys
import traceback

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

try:
    requests.packages.urllib3.disable_warnings()
    import urllib3
    urllib3.disable_warnings()
except:
    pass

DEFAULT_UA = 'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0'

class BasePluginInternal(controller.CementBaseController):
    DEFAULT_UA = DEFAULT_UA
    not_found_url = "misc/test/error/404/ispresent.html"
    NUMBER_DEFAULT = 'number_default'
    NUMBER_THEMES_DEFAULT = 350
    NUMBER_PLUGINS_DEFAULT = 1000

    out = None
    session = None
    vf = None

    class Meta:
        label = 'baseplugin'
        stacked_on = 'scan'

        argument_formatter = common.SmartFormatter

        epilog = template('help_epilog.mustache')

    def _path(self, path, pwd):
        if path.startswith('/'):
            return path
        else:
            return pwd + "/" + path

    def _threads(self, pargs):
        threads = pargs.threads
        if pargs.threads_identify:
            threads_identify = pargs.threads_identify
        else:
            threads_identify = threads

        if pargs.threads_scan:
            threads_scan = pargs.threads_scan
        else:
            threads_scan = threads

        if pargs.threads_enumerate:
            threads_enumerate = pargs.threads_enumerate
        else:
            threads_enumerate = threads

        return threads, threads_identify, threads_scan, threads_enumerate

    def _options(self, pargs):
        pwd = os.getcwd()
        if pargs.url_file != None:
            url_file = self._path(pargs.url_file, pwd)
        else:
            url = pargs.url

        enumerate = pargs.enumerate
        verb = pargs.verb
        method = pargs.method
        output = pargs.output
        timeout = pargs.timeout
        timeout_host = pargs.timeout_host
        hide_progressbar = pargs.hide_progressbar
        debug_requests = pargs.debug_requests
        follow_redirects = pargs.follow_redirects
        plugins_base_url = pargs.plugins_base_url
        themes_base_url = pargs.themes_base_url
        debug = pargs.debug
        resume = pargs.resume
        number = pargs.number if not pargs.number == 'all' else 100000
        if pargs.error_log:
            error_log = self._path(pargs.error_log, pwd)
        else:
            error_log = '-'

        headers = {}
        if pargs.host:
            headers = {'Host': pargs.host}

        threads, threads_identify, threads_scan, threads_enumerate = self._threads(pargs)

        if pargs.massscan_override:
            threads = 10
            threads_identify = 500
            threads_scan = 500
            threads_enumerate = 10
            timeout = 30
            timeout_host = 300

        del pargs
        return locals()

    def _base_kwargs(self, opts):
        kwargs_plugins = {
            'threads': opts['threads_enumerate'],
            'verb': opts['verb'],
            'timeout': opts['timeout'],
            'imu': getattr(self, 'interesting_module_urls', None)
        }

        return dict(kwargs_plugins)

    def _functionality(self, opts):
        kwargs_base = self._base_kwargs(opts)

        plugins_base_url = opts['plugins_base_url']
        themes_base_url = opts['themes_base_url']
        if not plugins_base_url:
            plugins_base_url = self.plugins_base_url
        if not themes_base_url:
            themes_base_url = self.themes_base_url

        kwargs_plugins = dict_combine(kwargs_base, {
            'base_url': plugins_base_url,
            'max_plugins': opts['number'],
            'headers': opts['headers']
        })

        kwargs_themes = dict(kwargs_plugins)
        kwargs_themes['base_url'] = themes_base_url

        if opts['number'] == self.NUMBER_DEFAULT:
            kwargs_themes['max_plugins'] = self.NUMBER_THEMES_DEFAULT
            kwargs_plugins['max_plugins'] = self.NUMBER_PLUGINS_DEFAULT

        all = {
            'plugins': {
                'func': self.enumerate_plugins,
                'template': 'enumerate_plugins.mustache',
                'kwargs': kwargs_plugins
            },
            'themes': {
                'func': self.enumerate_themes,
                'template': 'enumerate_plugins.mustache',
                'kwargs': kwargs_themes
            },
            'version': {
                'func': self.enumerate_version,
                'template': 'enumerate_version.mustache',
                'kwargs': {
                    'verb': opts['verb'],
                    'threads': opts['threads_enumerate'],
                    'timeout': opts['timeout'],
                    'headers': opts['headers']
                }
            },
            'interesting urls': {
                'func': self.enumerate_interesting,
                'template': 'enumerate_interesting.mustache',
                'kwargs': {
                    'verb': opts['verb'],
                    'interesting_urls': self.interesting_urls,
                    'threads': opts['threads_enumerate'],
                    'timeout': opts['timeout'],
                    'headers': opts['headers']
                }
            },
        }

        return all

    def _enabled_functionality(self, functionality, opts):
        enabled_functionality = {}
        if opts['enumerate'] == 'p':
            enabled_functionality['plugins'] = functionality['plugins']
        elif opts['enumerate'] == 't':
            enabled_functionality['themes'] = functionality['themes']
        elif opts['enumerate'] == 'u':
            enabled_functionality['users'] = functionality['users']
        elif opts['enumerate'] == 'v':
            enabled_functionality['version'] = functionality['version']
        elif opts['enumerate'] == 'i':
            enabled_functionality['interesting urls'] = functionality['interesting urls']
        elif opts['enumerate'] == 'a':
            enabled_functionality = functionality

        if not self.can_enumerate_plugins and 'plugins' in enabled_functionality:
            del enabled_functionality['plugins']

        if not self.can_enumerate_themes and 'themes' in enabled_functionality:
            del enabled_functionality['themes']

        if not self.can_enumerate_interesting and 'interesting urls' in enabled_functionality:
            del enabled_functionality['interesting urls']

        if not self.can_enumerate_version and 'version' in enabled_functionality:
            del enabled_functionality['version']

        return enabled_functionality

    def _output(self, opts):
        if opts['output'] == 'json' or 'url_file' in opts:
            output = JsonOutput(error_log=opts['error_log'])
        else:
            output = StandardOutput(error_log=opts['error_log'])

        if opts['debug']:
            output.debug_output = True

        return output

    def _general_init(self, opts, out=None):
        """
            Initializes a variety of variables depending on user input.

            @return: a tuple containing a boolean value indicating whether
            progressbars should be hidden, functionality and enabled
            functionality.
        """

        self.session = Session()
        if out:
            self.out = out
        else:
            self.out = self._output(opts)

        is_cms_plugin = self._meta.label != "scan"
        if is_cms_plugin:
            self.vf = VersionsFile(self.versions_file)

        # http://stackoverflow.com/questions/23632794/in-requests-library-how-can-i-avoid-httpconnectionpool-is-full-discarding-con
        try:
            a = requests.adapters.HTTPAdapter(pool_maxsize=5000)
            self.session.mount('http://', a)
            self.session.mount('https://', a)
            self.session.cookies.set_policy(BlockAll())
        except AttributeError:
            old_req = """Running a very old version of requests! Please `pip
                install -U requests`."""
            self.out.warn(old_req)

        self.session.verify = False
        self.session.headers['User-Agent'] = self.DEFAULT_UA

        debug_requests = opts['debug_requests']
        if debug_requests:
            hide_progressbar = True
            opts['threads_identify'] = 1
            opts['threads_scan'] = 1
            opts['threads_enumerate'] = 1
            self.session = RequestsLogger(self.session)
        else:
            if opts['hide_progressbar']:
                hide_progressbar = True
            else:
                hide_progressbar = False

        functionality = self._functionality(opts)
        enabled_functionality = self._enabled_functionality(functionality, opts)

        return (hide_progressbar, functionality, enabled_functionality)

    def plugin_init(self):
        time_start = datetime.now()
        opts = self._options(self.app.pargs)
        hide_progressbar, functionality, enabled_functionality = self._general_init(opts)

        if 'url_file' in opts:
            self.process_url_file(opts, functionality, enabled_functionality)
        else:
            self.process_url(opts, functionality, enabled_functionality, hide_progressbar)

        self.out.close()

        if not common.shutdown:
            self.out.echo('\033[95m[+] Scan finished (%s elapsed)\033[0m' %
                    str(datetime.now() - time_start))
        else:
            sys.exit(130)

    def process_url(self, opts, functionality, enabled_functionality, hide_progressbar):
        try:
            url = (opts['url'], opts['headers']['Host'])
        except:
            url = opts['url']

        if not url:
            self.out.fatal("--url parameter is blank.")

        output = self.url_scan(url, opts, functionality, enabled_functionality,
                hide_progressbar=hide_progressbar)

        if not common.shutdown:
            self.out.result(output, functionality)

    def process_url_iterable(self, iterable, opts, functionality, enabled_functionality):
        self.out.debug('base_plugin_internal.process_url_iterable')
        timeout_host = opts['timeout_host']

        i = 0
        with ThreadPoolExecutor(max_workers=opts['threads_scan']) as executor:
            results = []
            for url in iterable:

                args = [url, opts, functionality, enabled_functionality, True]
                future = executor.submit(self.url_scan, *args)

                url_to_log = str(url).rstrip()

                results.append({
                    'future': future,
                    'url': url_to_log,
                })

                if i % 1000 == 0 and i != 0:
                    self._process_results_multisite(results,
                            functionality, timeout_host)
                    results = []

                i += 1

            if len(results) > 0:
                self._process_results_multisite(results, functionality,
                        timeout_host)
                results = []

    def _process_results_multisite(self, results, functionality, timeout_host):
        for result in results:
            try:
                if common.shutdown:
                    result['future'].cancel()
                    continue

                output = result['future'].result(timeout=timeout_host)

                output['host'] = result['url']
                output['cms_name'] = self._meta.label

                if not common.shutdown:
                    self.out.result(output, functionality)

            except:
                if self.app != None:
                    testing = self.app.testing
                else:
                    testing = None

                f.exc_handle(result['url'], self.out, testing)

    def process_url_file(self, opts, functionality, enabled_functionality):
        file_location = opts['url_file']
        with open(file_location) as url_file:
            self.check_file_empty(file_location)
            self.resume_forward(url_file, opts['resume'], opts['url_file'],
                opts['error_log'])

            self.process_url_iterable(url_file, opts, functionality, enabled_functionality)

    def url_scan(self, url, opts, functionality, enabled_functionality, hide_progressbar):
        """
        This is the main function called whenever a URL needs to be scanned.
        This is called when a user specifies an individual CMS, or after CMS
        identification has taken place. This function is called for individual
        hosts specified by `-u` or for individual lines specified by `-U`.
        @param url: this parameter can either be a URL or a (url, host_header)
            tuple. The url, if a string, can be in the format of url + " " +
            host_header.
        @param opts: options object as returned by self._options().
        @param functionality: as returned by self._general_init.
        @param enabled_functionality: as returned by self._general_init.
        @param hide_progressbar: whether to hide the progressbar.
        @return: results dictionary.
        """
        self.out.debug('base_plugin_internal.url_scan -> %s' % str(url))
        if isinstance(url, tuple):
            url, host_header = url
        else:
            url, host_header = self._process_host_line(url)

        url = common.repair_url(url)
        if opts['follow_redirects']:
            url, host_header = self.determine_redirect(url, host_header, opts)

        need_sm = opts['enumerate'] in ['a', 'p', 't']
        if need_sm and (self.can_enumerate_plugins or self.can_enumerate_themes):
            scanning_method = opts['method']
            if not scanning_method:
                scanning_method = self.determine_scanning_method(url,
                        opts['verb'], opts['timeout'], self._generate_headers(host_header))

        else:
            scanning_method = None

        enumerating_all = opts['enumerate'] == 'a'
        result = {}
        for enumerate in enabled_functionality:
            enum = functionality[enumerate]

            if common.shutdown:
                continue

            # Get the arguments for the function.
            kwargs = dict(enum['kwargs'])
            kwargs['url'] = url
            kwargs['hide_progressbar'] = hide_progressbar
            if enumerate in ['themes', 'plugins']:
                kwargs['scanning_method'] = scanning_method

            kwargs['headers'] = self._generate_headers(host_header)

            # Call to the respective functions occurs here.
            finds, is_empty = enum['func'](**kwargs)

            result[enumerate] = {'finds': finds, 'is_empty': is_empty}

        return result

    def _determine_redirect(self, url, verb, timeout=15, headers={}):
        """
        Internal redirect function, focuses on HTTP and worries less about
        application-y stuff.
        @param url: the url to check
        @param verb: the verb, e.g. head, or get.
        @param timeout: the time, in seconds, that requests should wait
            before throwing an exception.
        @param headers: a set of headers as expected by requests.
        @return: the url that needs to be scanned. It may be equal to the url
            parameter if no redirect is needed.
        """
        requests_verb = getattr(self.session, verb)
        r = requests_verb(url, timeout=timeout, headers=headers, allow_redirects=False)

        redirect = 300 <= r.status_code < 400
        url_new = url
        if redirect:
            redirect_url = r.headers['Location']
            url_new = redirect_url

            relative_redirect = not redirect_url.startswith('http')
            if relative_redirect:
                url_new = url

            base_redir = base_url(redirect_url)
            base_supplied = base_url(url)

            same_base = base_redir == base_supplied
            if same_base:
                url_new = url

        return url_new

    def determine_redirect(self, url, host_header, opts):
        """
        Determines whether scanning a different request is suggested by the
        remote host. This function should be called only if
        opts['follow_redirects'] is true.
        @param url: the base url as returned by self._process_host_line.
        @param host_header: host header as returned by self._process_host_line.
        @param opts: the options as returned by self._options.
        @return: a tuple of the final url, host header. This may be the same
            objects passed in if no change is required.
        """
        orig_host_header = host_header
        redir_url = self._determine_redirect(url, opts['verb'],
                opts['timeout'], self._generate_headers(host_header))

        redirected = redir_url != url
        if redirected:
            self.out.echo('[+] Accepted redirect to %s' % redir_url)
            contains_host = orig_host_header != None
            if contains_host:
                parsed = urlparse(redir_url)
                dns_lookup_required = parsed.netloc != orig_host_header
                if dns_lookup_required:
                    url = redir_url
                    host_header = None
                else:
                    orig_parsed = urlparse(url)
                    parsed = parsed._replace(netloc=orig_parsed.netloc)
                    url = parsed.geturl()

            else:
                url = redir_url

        return url, host_header

    def _determine_ok_200(self, requests_verb, url):
        if common.is_string(self.regular_file_url):
            reg_url = url + self.regular_file_url
            ok_resp = requests_verb(reg_url)
            ok_200 = ok_resp.status_code == 200
        else:
            ok_200 = False
            for path in self.regular_file_url:
                reg_url = url + path
                ok_resp = requests_verb(reg_url)
                if ok_resp.status_code == 200:
                    ok_200 = True
                    break

        len_content = len(ok_resp.content)

        return ok_200, len_content

    def _determine_fake_200(self, requests_verb, url):
        response = requests_verb(url + self.not_found_url)

        return response.status_code == 200, len(response.content)

    def determine_scanning_method(self, url, verb, timeout=15, headers={}):
        requests_verb = partial(getattr(self.session, verb), timeout=timeout,
                headers=headers)

        folder_resp = requests_verb(url + self.forbidden_url)
        ok_200, reg_url_len = self._determine_ok_200(requests_verb, url)
        fake_200, fake_200_len = self._determine_fake_200(requests_verb, url)

        # Websites which return 200 for not found URLs.
        diff_lengths_above_threshold = abs(fake_200_len - reg_url_len) > 25
        if fake_200 and not diff_lengths_above_threshold:
            self.out.warn("""Website responds with 200 for all URLs and
                    doesn't seem to be running %s.""" % self._meta.label)
            ok_200 = False

        folder_300 = 300 < folder_resp.status_code < 400
        if folder_resp.status_code == 403 and ok_200:
            return ScanningMethod.forbidden
        elif folder_resp.status_code == 404 and ok_200:
            self.out.warn('Known %s folders have returned 404 Not Found. If a module does not have a %s file it will not be detected.' %
                    (self._meta.label, self.module_common_file))
            return ScanningMethod.not_found
        elif folder_resp.status_code == 200 and ok_200:
            return ScanningMethod.ok
        elif folder_300 and ok_200:
            self.out.warn('Server returns redirects for folders. If a module does not have a %s file it will not be detected.' %
                    self.module_common_file)
            return ScanningMethod.not_found
        else:
            self._error_determine_scanning(url, folder_resp, ok_200)

    def _error_determine_scanning(self, url, folder_resp, ok_200):
        ok_human = '200 status' if ok_200 else 'not found status'
        info = '''Expected folder returned status '%s', expected file returned %s.''' % (folder_resp.status_code, ok_human)

        self.out.warn(info)
        self.out.fatal('It is possible that ''%s'' is not running %s. If you disagree, please specify a --method.' % (url, self._meta.label))

    def plugins_get(self, amount=100000):
        amount = int(amount)
        with open(self.plugins_file) as f:
            i = 0
            for plugin in f:
                if i >= amount:
                    break
                yield plugin.strip()
                i += 1

    def themes_get(self, amount=100000):
        amount = int(amount)
        with open(self.themes_file) as f:
            i = 0
            for theme in f:
                if i>= amount:
                    break
                yield theme.strip()
                i +=1

    def enumerate(self, url, base_url_supplied, scanning_method,
            iterator_returning_method, iterator_len, max_iterator=500, threads=10,
            verb='head', timeout=15, hide_progressbar=False, imu=None, headers={}):
        '''
            @param url: base URL for the website.
            @param base_url_supplied: Base url for themes, plugins. E.g. '%ssites/all/modules/%s/'
            @param scanning_method: see ScanningMethod
            @param iterator_returning_method: a function which returns an
                element that, when iterated, will return a full list of plugins
            @param iterator_len: the number of items the above iterator can
                return, regardless of user preference.
            @param max_iterator: integer that will be passed unto iterator_returning_method
            @param threads: number of threads
            @param verb: what HTTP verb. Valid options are 'get' and 'head'.
            @param timeout: the time, in seconds, that requests should wait
                before throwing an exception.
            @param hide_progressbar: if true, the progressbar will not be
                displayed.
            @param imu: Interesting module urls. A list containing tuples in the
                following format [('readme.txt', 'default readme')].
            @param headers: List of custom headers as expected by requests.
        '''
        if common.is_string(base_url_supplied):
            base_urls = [base_url_supplied]
        else:
            base_urls = base_url_supplied

        requests_verb = getattr(self.session, verb)
        futures = []
        with ThreadPoolExecutor(max_workers=threads) as executor:
            for base_url in base_urls:
                plugins = iterator_returning_method(max_iterator)

                if scanning_method == ScanningMethod.not_found:
                    url_template = base_url + self.module_common_file
                else:
                    url_template = base_url

                for plugin_name in plugins:
                    plugin_url = url_template % (url, plugin_name)
                    future = executor.submit(requests_verb, plugin_url,
                            timeout=timeout, headers=headers)

                    if plugin_url.endswith('/'):
                        final_url = plugin_url
                    else:
                        final_url = dirname(plugin_url) + "/"

                    futures.append({
                        'base_url': base_url,
                        'future': future,
                        'plugin_name': plugin_name,
                        'plugin_url': final_url,
                    })

            if not hide_progressbar:
                max_possible = max_iterator if int(max_iterator) < int(iterator_len) else iterator_len
                items_total = int(max_possible) * len(base_urls)
                p = ProgressBar(sys.stderr, items_total, "modules")

            if scanning_method == ScanningMethod.forbidden:
                expected_status = [403]
            else:
                expected_status = [200, 403]

            no_results = True
            found = []
            for future_array in futures:
                if common.shutdown:
                    future_array['future'].cancel()
                    continue

                if not hide_progressbar:
                    p.increment_progress()

                try:
                    r = future_array['future'].result()
                except requests.exceptions.ReadTimeout:
                    self.out.warn('\rGot a read timeout. Is the server overloaded? This may affect the results of your scan')
                    continue
                    
                if r.status_code in expected_status:
                    plugin_url = future_array['plugin_url']
                    plugin_name = future_array['plugin_name']

                    no_results = False
                    found.append({
                        'name': plugin_name,
                        'url': plugin_url
                    })
                elif r.status_code >= 500:
                    self.out.warn('\rGot a 500 error. Is the server overloaded?')

            if not hide_progressbar:
                p.hide()

        if not common.shutdown and (imu != None and not no_results):
            found = self._enumerate_plugin_if(found, verb, threads, imu,
                    hide_progressbar, timeout=timeout, headers=headers)

        return found, no_results

    def enumerate_plugins(self, url, base_url, scanning_method='forbidden',
            max_plugins=500, threads=10, verb='head', timeout=15,
            hide_progressbar=False, imu=None, headers={}):

        iterator = self.plugins_get
        iterator_len = file_len(self.plugins_file)

        return self.enumerate(url, base_url, scanning_method, iterator,
                iterator_len, max_plugins, threads, verb,
                timeout, hide_progressbar, imu, headers)

    def enumerate_themes(self, url, base_url, scanning_method='forbidden',
            max_plugins=500, threads=10, verb='head', timeout=15,
            hide_progressbar=False, imu=None, headers={}):

        iterator = self.themes_get
        iterator_len = file_len(self.themes_file)

        return self.enumerate(url, base_url, scanning_method, iterator,
                iterator_len, max_plugins, threads, verb, timeout,
                hide_progressbar, imu, headers)

    def enumerate_interesting(self, url, interesting_urls, threads=10,
            verb='head', timeout=15, hide_progressbar=False, headers={}):
        requests_verb = getattr(self.session, verb)

        if not hide_progressbar:
            p = ProgressBar(sys.stderr, len(interesting_urls),
                    "interesting")

        found = []
        for path, description in interesting_urls:

            if common.shutdown:
                continue

            interesting_url = url + path
            resp = requests_verb(interesting_url, timeout=timeout,
                    headers=headers)

            if resp.status_code == 200 or resp.status_code == 301:
                found.append({
                    'url': interesting_url,
                    'description': description
                })

            if not hide_progressbar:
                p.increment_progress()

        if not hide_progressbar:
            p.hide()

        return found, len(found) == 0

    def enumerate_version(self, url, threads=10, verb='head',
            timeout=15, hide_progressbar=False, headers={}):
        """
        Determines which version of CMS is installed at url. This is done by
        comparing file hashes against the database of hashes in
        self.version_file, which is located at dscan/plugins/<plugin_name>/versions.xml
        @param url: the url to check.
        @param threads: the number of threads to use for this scan.
        @param verb: HTTP verb to use.
        @param timeout: time, in seconds, before timing out a request.
        @param hide_progressbar: should the function hide the progressbar?
        @param headers: a dict of headers to pass to requests.get.
        @return (possible_versions, is_empty)
        """

        files = self.vf.files_get()
        changelogs = self.vf.changelogs_get()

        if not hide_progressbar:
            p = ProgressBar(sys.stderr, len(files) +
                    len(changelogs), "version")

        hashes = {}
        futures = {}
        with ThreadPoolExecutor(max_workers=threads) as executor:
            for file_url in files:
                futures[file_url] = executor.submit(self.enumerate_file_hash,
                        url, file_url=file_url, timeout=timeout, headers=headers)

            for file_url in futures:
                if common.shutdown:
                    futures[file_url].cancel()
                    continue

                try:
                    hsh = futures[file_url].result()
                    hashes[file_url] = hsh
                except RuntimeError:
                    pass

                if not hide_progressbar:
                    p.increment_progress()

        version = self.vf.version_get(hashes)

        # Narrow down using changelog, if accurate.
        if self.vf.has_changelog():
            version = self.enumerate_version_changelog(url, version, timeout, headers=headers)

        if not hide_progressbar:
            p.increment_progress()
            p.hide()

        return version, len(version) == 0

    def enumerate_version_changelog(self, url, versions_estimated, timeout=15,
            headers={}):
        """
        If we have a changelog in store for this CMS, this function will be
        called, and a changelog will be used for narrowing down which version is
        installed. If the changelog's version is outside our estimated range,
        it is discarded.
        @param url: the url to check against.
        @param versions_estimated: the version other checks estimate the
            installation is.
        @param timeout: the number of seconds to wait before expiring a request.
        @param headers: headers to pass to requests.get()
        """
        changelogs = self.vf.changelogs_get()
        ch_hash = None
        for ch_url in changelogs:
            try:
                ch_hash = self.enumerate_file_hash(url, file_url=ch_url,
                        timeout=timeout, headers=headers)
            except RuntimeError:
                pass

        ch_version = self.vf.changelog_identify(ch_hash)
        if ch_version in versions_estimated:
            return [ch_version]
        else:
            return versions_estimated

    def enumerate_file_hash(self, url, file_url, timeout=15, headers={}):
        """
        Gets the MD5 of requests.get(url + file_url).
        @param url: the installation's base URL.
        @param file_url: the url of the file to hash.
        @param timeout: the number of seconds to wait prior to a timeout.
        @param headers: a dictionary to pass to requests.get()
        """
        r = self.session.get(url + file_url, timeout=timeout, headers=headers)
        if r.status_code == 200:
            hash = hashlib.md5(r.content).hexdigest()
            return hash
        else:
            raise RuntimeError("File '%s' returned status code '%s'." % (file_url, r.status_code))

    def _enumerate_plugin_if(self, found_list, verb, threads, imu_list,
            hide_progressbar, timeout=15, headers={}):
        """
        Finds interesting urls within a plugin folder which respond with 200 OK.
        @param found_list: as returned in self.enumerate. E.g. [{'name':
            'this_exists', 'url': 'http://adhwuiaihduhaknbacnckajcwnncwkakncw.com/sites/all/modules/this_exists/'}]
        @param verb: the verb to use.
        @param threads: the number of threads to use.
        @param imu_list: Interesting module urls.
        @param hide_progressbar: whether to display a progressbar.
        @param timeout: timeout in seconds for http requests.
        @param headers: custom headers as expected by requests.
        """

        if not hide_progressbar:
            p = ProgressBar(sys.stderr, len(found_list) *
                    len(imu_list), name="IMU")

        requests_verb = getattr(self.session, verb)
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = []
            for i, found in enumerate(found_list):
                found_list[i]['imu'] = []
                for imu in imu_list:
                    interesting_url = found['url'] + imu[0]
                    future = executor.submit(requests_verb, interesting_url,
                            timeout=timeout, headers=headers)

                    futures.append({
                        'url': interesting_url,
                        'future': future,
                        'description': imu[1],
                        'i': i
                    })

            for f in futures:
                if common.shutdown:
                    futures[file_url].cancel()
                    continue

                r = f['future'].result()
                if r.status_code == 200:
                    found_list[f['i']]['imu'].append({
                        'url': f['url'],
                        'description': f['description']
                    })

                if not hide_progressbar:
                    p.increment_progress()

        if not hide_progressbar:
            p.hide()

        return found_list

    def cms_identify(self, url, timeout=15, headers={}):
        """
        Function called when attempting to determine if a URL is identified
        as being this particular CMS.
        @param url: the URL to attempt to identify.
        @param timeout: number of seconds before a timeout occurs on a http
            connection.
        @param headers: custom HTTP headers as expected by requests.
        @return: a boolean value indiciating whether this CMS is identified
            as being this particular CMS.
        """
        self.out.debug("cms_identify")
        if isinstance(self.regular_file_url, str):
            rfu = [self.regular_file_url]
        else:
            rfu = self.regular_file_url

        is_cms = False
        for regular_file_url in rfu:
            try:
                hash = self.enumerate_file_hash(url, regular_file_url, timeout,
                        headers)
            except RuntimeError:
                continue

            hash_exists = self.vf.has_hash(hash)
            if hash_exists:
                is_cms = True
                break

        return is_cms

    def _process_host_line(self, line):
        return f.process_host_line(line)

    def _generate_headers(self, host_header):
        if host_header:
            return {'Host': host_header}
        else:
            return None

    def check_file_empty(self, file_location):
        """
        Performs os.stat on file_location and raises FileEmptyException if the
        file is empty.
        @param file_location: a string containing the location of the file.
        """
        if os.stat(file_location).st_size == 0:
            raise FileEmptyException("File '%s' is empty." % file_location)

    def resume(self, url_file, error_log):
        """
        @param url_file: opts[url_file]
        @param error_log: opts[error_log]
        @return: the number of lines to skip for resume functionality.
        """
        with open(url_file) as url_fh:
            with open(error_log, 'rb') as error_fh:
                last_100 = f.tail(error_fh, 100)
                for l in reversed(last_100):
                    if l.startswith("["):
                        try:
                            orig_line = l.split("Line ")[1].split(' \'')[0]
                        except IndexError:
                            raise CannotResumeException("Could not parse original line from line '%s'" % l)

                        break
                else:
                    raise CannotResumeException('Could not find line to restore in file "%s"' % error_log)

                for line_nb, line in enumerate(url_fh, start=1):
                    if line.strip() == orig_line:
                        orig_line_nb = line_nb
                        break
                else:
                    raise CannotResumeException('Could not find line "%s" in file "%s"' % (orig_line, url_file))

                return orig_line_nb

    def resume_forward(self, fh, resume, file_location, error_log):
        """
        Forwards `fh` n lines, where n lines is the amount of lines we should
        skip in order to resume our previous scan, if resume is required by the
        user.
        @param fh: fh to advance.
        @param file_location: location of the file handler in disk.
        @param error_log: location of the error_log in disk.
        """
        if resume:
            if not error_log:
                raise CannotResumeException("--error-log not provided.")

            skip_lines = self.resume(file_location, error_log)
            for _ in range(skip_lines):
                next(fh)

