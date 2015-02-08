from __future__ import print_function
from cement.core import handler, controller
from common import ScanningMethod, ProgressBar, StandardOutput, JsonOutput, \
        VersionsFile, RequestsLogger
from common import template, enum_list, dict_combine, base_url, file_len
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from os.path import dirname
from requests import Session
import common
import hashlib
import requests
import signal
import sys
import traceback

global shutdown
shutdown = False
def handle_interrupt(signal, stack):
    print("\nShutting down...")
    global shutdown
    shutdown = True

signal.signal(signal.SIGINT, handle_interrupt)

# https://github.com/kennethreitz/requests/issues/2214
try:
    requests.packages.urllib3.disable_warnings()
except:
    pass

class BasePluginInternal(controller.CementBaseController):
    requests = None
    out = None
    DEFAULT_UA = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36'
    not_found_url = "misc/test/error/404/ispresent.html"

    class Meta:
        label = 'baseplugin'
        stacked_on = 'scan'

        argument_formatter = common.SmartFormatter

        epilog = template('help_epilog.tpl')

    def getattr(self, pargs, attr_name, default=None):
        val = getattr(pargs, attr_name)
        if val:
            return val
        else:
            try:
                return getattr(self, attr_name)
            except AttributeError:
                return default

    def _general_init(self, output=None, user_agent=None, debug_requests=False):
        self.session = Session()

        # http://stackoverflow.com/questions/23632794/in-requests-library-how-can-i-avoid-httpconnectionpool-is-full-discarding-con
        a = requests.adapters.HTTPAdapter(pool_maxsize=5000)
        self.session.mount('http://', a)
        self.session.mount('https://', a)

        self.session.verify = False
        if not user_agent:
            user_agent = self.DEFAULT_UA

        self.session.headers['User-Agent'] = user_agent
        if debug_requests:
            self.session = RequestsLogger(self.session)

        if not output:
            self.out = StandardOutput()
        else:
            self.out = output

    def _options(self):
        pargs = self.app.pargs

        if pargs.url_file != None:
            url_file = pargs.url_file
        else:
            url = pargs.url

        threads = pargs.threads
        enumerate = pargs.enumerate
        verb = pargs.verb
        method = pargs.method
        output = pargs.output
        timeout = pargs.timeout
        timeout_host = pargs.timeout_host
        error_log = pargs.error_log
        debug_requests = pargs.debug_requests
        follow_redirects = pargs.follow_redirects
        number = pargs.number if not pargs.number == 'all' else 100000

        plugins_base_url = self.getattr(pargs, 'plugins_base_url')
        themes_base_url = self.getattr(pargs, 'themes_base_url')

        # all variables here will be returned.
        return locals()

    def _base_kwargs(self, opts):
        kwargs_plugins = {
            'threads': opts['threads'],
            'verb': opts['verb'],
            'timeout': opts['timeout'],
            'imu': getattr(self, 'interesting_module_urls', None)
        }

        return dict(kwargs_plugins)

    def _functionality(self, opts):
        kwargs_base = self._base_kwargs(opts)
        kwargs_plugins = dict_combine(kwargs_base, {
            'base_url': opts['plugins_base_url'],
            'max_plugins': opts['number']
        })

        kwargs_themes = dict(kwargs_plugins)
        kwargs_themes['base_url'] = opts['themes_base_url']

        all = {
            'plugins': {
                'func': getattr(self, 'enumerate_plugins'),
                'template': 'enumerate_plugins.tpl',
                'kwargs': kwargs_plugins
            },
            'themes': {
                'func': getattr(self, 'enumerate_themes'),
                'template': 'enumerate_plugins.tpl',
                'kwargs': kwargs_themes
            },
            'version': {
                'func': getattr(self, 'enumerate_version'),
                'template': 'enumerate_version.tpl',
                'kwargs': {
                    'versions_file': self.versions_file,
                    'verb': opts['verb'],
                    'threads': opts['threads'],
                    'timeout': opts['timeout']
                }
            },
            'interesting urls': {
                'func': getattr(self, 'enumerate_interesting'),
                'template': 'enumerate_interesting.tpl',
                'kwargs': {
                    'verb': opts['verb'],
                    'interesting_urls': self.interesting_urls,
                    'threads': opts['threads'],
                    'timeout': opts['timeout']
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

    def _process_results_multisite(self, results, functionality, timeout_host):
        for result in results:
            try:
                if shutdown:
                    result['future'].cancel()
                    continue

                output = result['future'].result(timeout=timeout_host)

                output['host'] = result['url']
                if not shutdown:
                    self.out.result(output, functionality)

            except:
                exc = traceback.format_exc()
                print(exc)
                self.out.warn(exc, whitespace_strp=False)

    def plugin_init(self):
        time_start = datetime.now()
        opts = self._options()

        if opts['output'] == 'json' or 'url_file' in opts:
            output = JsonOutput(error_log=opts['error_log'])
        else:
            output = StandardOutput(error_log=opts['error_log'])

        debug_requests = opts['debug_requests']
        self._general_init(output=output, debug_requests=debug_requests)

        hide_progressbar = True if debug_requests else False
        if debug_requests:
            opts['threads'] = 1

        functionality = self._functionality(opts)
        enabled_functionality = self._enabled_functionality(functionality, opts)
        if 'url_file' in opts:
            with open(opts['url_file']) as url_file:
                timeout_host = opts['timeout_host']
                i = 0
                with ThreadPoolExecutor(max_workers=opts['threads']) as executor:
                    results = []
                    for url in url_file:
                        args = [url, opts, functionality, enabled_functionality,
                                True]

                        future = executor.submit(self.url_scan, *args)

                        results.append({
                            'future': future,
                            'url': url.rstrip('\n'),
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

        else:
            output = self.url_scan(opts['url'], opts, functionality,
                    enabled_functionality, hide_progressbar=hide_progressbar)

            if not shutdown:
                self.out.result(output, functionality)

        self.out.close()

        if not shutdown:
            self.out.echo('\033[95m[+] Scan finished (%s elapsed)\033[0m' %
                    str(datetime.now() - time_start))
        else:
            sys.exit(130)

    def url_scan(self, url, opts, functionality, enabled_functionality,
            hide_progressbar):

        url = common.validate_url(url, self.out)
        if opts['follow_redirects']:
            url = self.determine_redirect(url, opts['verb'], opts['timeout'])

        need_sm = opts['enumerate'] in ['a', 'p', 't']
        if need_sm and (self.can_enumerate_plugins or self.can_enumerate_themes):
            scanning_method = opts['method']
            if not scanning_method:
                scanning_method = self.determine_scanning_method(url,
                        opts['verb'], opts['timeout'])
        else:
            scanning_method = None

        enumerating_all = opts['enumerate'] == 'a'
        result = {}
        for enumerate in enabled_functionality:
            enum = functionality[enumerate]

            # Get the arguments for the function.
            kwargs = dict(enum['kwargs'])
            kwargs['url'] = url
            if enumerate in ['themes', 'plugins']:
                kwargs['scanning_method'] = scanning_method
                kwargs['hide_progressbar'] = hide_progressbar

            # Call to the respective functions occurs here.
            finds, is_empty = enum['func'](**kwargs)

            result[enumerate] = {'finds': finds, 'is_empty': is_empty}

        return result

    def determine_redirect(self, url, verb, timeout=15):
        """
            @param url the url to check
            @param verb the verb, e.g. head, or get.
            @param timeout the time, in seconds, that requests should wait
                before throwing an exception.
            @return the url that needs to be scanned. It may be equal to the url
                parameter if no redirect is needed.
        """
        requests_verb = getattr(self.session, verb)
        r = requests_verb(url, timeout=timeout)

        redirect = 300 <= r.status_code < 400
        url_new = url
        if redirect:
            redirect_url = url_new = r.headers['Location']

            relative_redirect = not redirect_url.startswith('http')
            if relative_redirect:
                url_new = url

            base_redir = base_url(redirect_url)
            base_supplied = base_url(url)

            same_base = base_redir == base_supplied
            if same_base:
                url_new = url

        return url_new

    def _determine_ok_200(self, requests_verb, url, timeout):
        if common.is_string(self.regular_file_url):
            reg_url = url + self.regular_file_url
            ok_resp = requests_verb(reg_url, timeout=timeout)
            ok_200 = ok_resp.status_code == 200
        else:
            ok_200 = False
            for path in self.regular_file_url:
                reg_url = url + path
                ok_resp = requests_verb(reg_url, timeout=timeout)
                if ok_resp.status_code == 200:
                    ok_200 = True
                    break

        len_content = len(ok_resp.content)

        return ok_200, len_content

    def _determine_fake_200(self, requests_verb, url, timeout):
        response = requests_verb(url + self.not_found_url,
                    timeout=timeout)

        return response.status_code == 200, len(response.content)

    def determine_scanning_method(self, url, verb, timeout=15):
        requests_verb = getattr(self.session, verb)
        folder_resp = requests_verb(url + self.forbidden_url, timeout=timeout)
        ok_200, reg_url_len = self._determine_ok_200(requests_verb, url, timeout)
        fake_200, fake_200_len = self._determine_fake_200(requests_verb, url, timeout)

        # Websites which return 200 for not found URLs.
        diff_lengths_above_threshold = abs(fake_200_len - reg_url_len) > 25
        if fake_200 and not diff_lengths_above_threshold:
            self.out.warn("""Website responds with 200 for all URLs and
                    doesn't seem to be running %s.""" % self._meta.label)
            ok_200 = False

        if folder_resp.status_code == 403 and ok_200:
            return ScanningMethod.forbidden

        elif folder_resp.status_code == 404 and ok_200:
            self.out.warn('Known %s folders have returned 404 Not Found. If a module does not have a %s file it will not be detected.' %
                    (self._meta.label, self.module_common_file))
            return ScanningMethod.not_found

        elif folder_resp.status_code == 200 and ok_200:

            return ScanningMethod.ok
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
            verb='head', timeout=15, hide_progressbar=False, imu=None):
        '''
            @param url base URL for the website.
            @param base_url_supplied Base url for themes, plugins. E.g. '%ssites/all/modules/%s/'
            @param scanning_method see ScanningMethod
            @param iterator_returning_method a function which returns an
                element that, when iterated, will return a full list of plugins
            @param iterator_len the number of items the above iterator can
                return, regardless of user preference.
            @param max_iterator integer that will be passed unto iterator_returning_method
            @param threads number of threads
            @param verb what HTTP verb. Valid options are 'get' and 'head'.
            @param timeout the time, in seconds, that requests should wait
                before throwing an exception.
            @param hide_progressbar if true, the progressbar will not be
                displayed.
            @param imu Interesting module urls. A list containing tuples in the
                following format [('readme.txt', 'default readme')].
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
                            timeout=timeout)

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
                p = ProgressBar(sys.stderr)
                items_progressed = 0
                max_possible = max_iterator if int(max_iterator) < int(iterator_len) else iterator_len
                items_total = int(max_possible) * len(base_urls)

            no_results = True
            found = []
            for future_array in futures:

                if shutdown:
                    future_array['future'].cancel()
                    continue

                if not hide_progressbar:
                    items_progressed += 1
                    p.set(items_progressed, items_total)

                r = future_array['future'].result()
                if r.status_code in [200, 403]:
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

        if imu != None and not no_results:
            found = self._enumerate_plugin_if(found, verb, threads, imu)

        return found, no_results

    def enumerate_plugins(self, url, base_url, scanning_method='forbidden',
            max_plugins=500, threads=10, verb='head', timeout=15,
            hide_progressbar=False, imu=None):

        iterator = self.plugins_get
        iterator_len = file_len(self.plugins_file)

        return self.enumerate(url, base_url, scanning_method, iterator,
                iterator_len, max_plugins, threads, verb,
                timeout, hide_progressbar, imu)

    def enumerate_themes(self, url, base_url, scanning_method='forbidden',
            max_plugins=500, threads=10, verb='head', timeout=15,
            hide_progressbar=False, imu=None):

        iterator = self.themes_get
        iterator_len = file_len(self.themes_file)

        return self.enumerate(url, base_url, scanning_method, iterator,
                iterator_len, max_plugins, threads, verb, timeout,
                hide_progressbar, imu)

    def enumerate_interesting(self, url, interesting_urls, threads=10,
            verb='head', timeout=15):
        requests_verb = getattr(self.session, verb)

        found = []
        for path, description in interesting_urls:

            if shutdown:
                continue

            interesting_url = url + path
            resp = requests_verb(interesting_url, timeout=timeout)
            if resp.status_code == 200 or resp.status_code == 301:
                found.append({
                    'url': interesting_url,
                    'description': description,
                })

        return found, len(found) == 0

    def enumerate_version(self, url, versions_file, threads=10, verb='head', timeout=15):
        vf = VersionsFile(versions_file)

        hashes = {}
        futures = {}
        files = vf.files_get()
        with ThreadPoolExecutor(max_workers=threads) as executor:
            for file_url in files:
                futures[file_url] = executor.submit(self.enumerate_file_hash,
                        url, file_url=file_url, timeout=timeout)

            for file_url in futures:

                if shutdown:
                    futures[file_url].cancel()
                    continue

                try:
                    hsh = futures[file_url].result()
                    hashes[file_url] = hsh
                except RuntimeError:
                    pass

        version = vf.version_get(hashes)

        # Narrow down using changelog, if accurate.
        if vf.has_changelog():
            version = self.enumerate_version_changelog(url, version, vf, timeout)

        return version, len(version) == 0

    def enumerate_version_changelog(self, url, versions_estimated, vf, timeout=15):
        changelogs = vf.changelogs_get()
        ch_hash = None
        for ch_url in changelogs:
            try:
                ch_hash = self.enumerate_file_hash(url, file_url=ch_url,
                        timeout=timeout)
            except RuntimeError:
                pass

        ch_version = vf.changelog_identify(ch_hash)
        if ch_version in versions_estimated:
            return [ch_version]
        else:
            return versions_estimated

    def enumerate_file_hash(self, url, file_url, timeout=15):
        r = self.session.get(url + file_url, timeout=timeout)
        if r.status_code == 200:
            return hashlib.md5(r.content).hexdigest()
        else:
            raise RuntimeError("File '%s' returned status code '%s'." % (file_url, r.status_code))

    def _enumerate_plugin_if(self, found_list, verb, threads, imu_list):
        """
            Finds interesting urls within a plugin folder which return 200.
            @param found_list as returned in self.enumerate. E.g. [{'name': 'this_exists', 'url': 'http://adhwuiaihduhaknbacnckajcwnncwkakncw.com/sites/all/modules/this_exists/'}]
            @param verb the verb to use.
            @param threads the number of threads to use.
            @param imu Interesting module urls.
        """
        requests_verb = getattr(self.session, verb)
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = []
            for i, found in enumerate(found_list):
                found_list[i]['imu'] = []
                for imu in imu_list:
                    interesting_url = found['url'] + imu[0]
                    future = executor.submit(requests_verb, interesting_url)
                    futures.append({
                        'url': interesting_url,
                        'future': future,
                        'description': imu[1],
                        'i': i
                    })

            for f in futures:
                r = f['future'].result()
                if r.status_code == 200:
                    found_list[f['i']]['imu'].append({
                        'url': f['url'],
                        'description': f['description']
                    })

        return found_list
