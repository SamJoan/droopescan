from cement.core import handler, controller
from common import template, enum_list, dict_combine, base_url
from common import Verb, ScanningMethod, Enumerate, VersionsFile, ProgressBar, \
        StandardOutput, ValidOutputs, JsonOutput
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from distutils.util import strtobool
from requests import Session
import common, hashlib
import sys, tempfile, os, traceback

class AbstractArgumentController(controller.CementBaseController):

    class Meta:
        label = 'scan'
        description = 'cms scanning functionality.'
        stacked_on = 'base'
        stacked_type = 'nested'

        epilog = "\n"

        argument_formatter = common.SmartFormatter

        arguments = [
                (['-u', '--url'], dict(action='store', help='')),
                (['-U', '--url-file'], dict(action='store', help='''A file which
                    contains a list of URLs.''')),
                (['--enumerate', '-e'], dict(action='store', help='R|' +
                    template('help_enumerate.tpl'),
                    choices=enum_list(Enumerate), default='a')),
                (['--method'], dict(action='store', help='R|' +
                    template('help_method.tpl'), choices=enum_list(ScanningMethod))),
                (['--output', '-o'], dict(action='store', help='Output format',
                    choices=enum_list(ValidOutputs), default='standard')),
                (['--number', '-n'], dict(action='store', help='''Number of
                    words to attempt from the plugin/theme dictionary. Default
                    is 1000. Use -n 'all' to use all available.''', default=1000)),
                (['--plugins-base-url'], dict(action='store', help="""Location
                    where the plugins are stored by the CMS. Default is the CMS'
                    default location. First %%s in string will be replaced with
                    the url, and the second one will be replaced with the module
                    name. E.g. '%%ssites/all/modules/%%s/'""")),
                (['--themes-base-url'], dict(action='store', help='''Same as
                    above, but for themes.''')),
                (['--threads', '-t'], dict(action='store', help='''Number of
                    threads. Default 1.''', default=1, type=int)),
                (['--verb'], dict(action='store', help="""The HTTP verb to use;
                    the default option is head, except for version enumeration
                    requests, which are always get because we need to get the hash
                    from the file's contents""",
                default='head', choices=enum_list(Verb))),
            ]

class BasePluginInternal(controller.CementBaseController):

    requests = None
    out = None
    DEFAULT_UA = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36'

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

    def _general_init(self, output=None, user_agent=None):
        self.session = Session()
        self.session.verify = False
        if not user_agent:
            user_agent = self.DEFAULT_UA

        self.session.headers['User-Agent'] = user_agent

        if not output:
            self.out = StandardOutput()
        else:
            self.out = output

    def _options_and_session_init(self):
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
        number = pargs.number if not pargs.number == 'all' else 100000

        plugins_base_url = self.getattr(pargs, 'plugins_base_url')
        themes_base_url = self.getattr(pargs, 'themes_base_url')

        # all variables here will be returned.
        return locals()

    def _base_kwargs(self, opts):
        kwargs_plugins = {
            'threads': opts['threads'],
            'verb': opts['verb'],
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
                }
            },
            'interesting urls': {
                'func': getattr(self, 'enumerate_interesting'),
                'template': 'enumerate_interesting.tpl',
                'kwargs': {
                    'verb': opts['verb'],
                    'interesting_urls': self.interesting_urls,
                    'threads': opts['threads']
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

    def plugin_init(self):
        time_start = datetime.now()
        opts = self._options_and_session_init()

        if opts['output'] == 'json':
            output = JsonOutput()
            self._general_init(output=output)
        else:
            self._general_init()

        functionality = self._functionality(opts)
        enabled_functionality = self._enabled_functionality(functionality, opts)

        if 'url_file' in opts:
            with open(opts['url_file']) as url_file:
                with ThreadPoolExecutor(max_workers=opts['threads']) as executor:
                    results = []
                    for url in url_file:
                        args = [url, opts, functionality, enabled_functionality]

                        future = executor.submit(self.url_scan, *args)

                        results.append({
                            'future': future,
                            'url': url,
                        })

                    for result in results:
                        try:
                            output = result['future'].result()
                            self.out.result(output, functionality)
                        except:
                            exc = traceback.format_exc()
                            self.out.warn(exc)

        else:
            output = self.url_scan(opts['url'], opts, functionality,
                    enabled_functionality)

            self.out.result(output, functionality)

        self.out.echo('\033[95m[+] Scan finished (%s elapsed)\033[0m' %
                str(datetime.now() - time_start))

    def url_scan(self, url, opts, functionality, enabled_functionality):
        url = common.validate_url(url, self.out)

        if self.can_enumerate_plugins or self.can_enumerate_themes:
            scanning_method = opts['method']
            if not scanning_method:
                scanning_method, url = self.determine_scanning_method(url, opts['verb'])
        else:
            scanning_method = None

        enumerating_all = opts['enumerate'] == 'a'
        if enumerating_all:
            self.out.echo(common.template('scan_begin.tpl', {'noun': 'all', 'url':
                url}))

        result = {}
        for enumerate in enabled_functionality:
            if not enumerating_all:
                self.out.echo(common.template('scan_begin.tpl', {'noun': enumerate,
                    'url': url}))

            enum = functionality[enumerate]

            # Get the arguments for the function.
            kwargs = dict(enum['kwargs'])
            kwargs['url'] = url
            if enumerate in ['themes', 'plugins']:
                kwargs['scanning_method'] = scanning_method

            # Call to the respective functions occurs here.
            finds, is_empty = enum['func'](**kwargs)

            result[enumerate] = {'finds': finds, 'is_empty': is_empty}

        return result

    def determine_scanning_method(self, url, verb):
        """
            @param url the URL to determine scanning based on.
            @param verb the verb, e.g. head, or get.
            @return scanning_method, url. This is because in case of redirects,
                a new URL may be returned.
        """
        scanning_method = self._determine_scanning_method(url, verb)

        redirected = scanning_method not in enum_list(ScanningMethod)
        if redirected:
            new_url = scanning_method
            scanning_method = self._determine_scanning_method(new_url, verb)
        else:
            new_url = url

        return scanning_method, new_url

    def _determine_scanning_method(self, url, verb):
        requests_method = getattr(self.session, verb)
        folder_resp = requests_method(url + self.folder_url)

        if common.is_string(self.regular_file_url):
            reg = url + self.regular_file_url
            ok_resp = requests_method(url + self.regular_file_url)
            ok_200 = ok_resp.status_code == 200
        else:
            ok_200 = False
            reg = url + self.regular_file_url[-1]
            for path in self.regular_file_url:
                ok_resp = requests_method(url + path)
                if ok_resp.status_code == 200:
                    ok_200 = True
                    break

        # Detect redirects.
        folder_redirect = 300 <= folder_resp.status_code < 400
        if not ok_200 and folder_redirect:
            redirect_url = folder_resp.headers['Location']
            return base_url(redirect_url)

        if not ok_200:
            self.out.warn("Known regular file '%s' returned status code %s instead of 200 as expected." %
                    (reg, ok_resp.status_code))

        if folder_resp.status_code == 403 and ok_200:
            return ScanningMethod.forbidden
        if folder_resp.status_code == 404 and ok_200:
            self.out.warn('Known %s folders have returned 404 Not Found. If a module does not have a %s file it will not be detected.' %
                    (self._meta.label, self.module_readme_file))
            return ScanningMethod.not_found
        if folder_resp.status_code == 200 and ok_200:
            self.out.warn('Known folder names for %s are returning 200 OK. Is directory listing enabled?' % self._meta.label)
            return ScanningMethod.ok
        else:
            self._error_determine_scanning(folder_resp, folder_redirect, ok_200)

    def _error_determine_scanning(self, folder_resp, folder_redirect, ok_200):
        loc = folder_resp.headers['location'] if folder_redirect else 'not present as not a redirect'
        ok_human = '200 status' if ok_200 else 'non-200 status.'
        info = '''Expected folder returned status '%s' (location header
            %s), expected file returned %s.''' % (folder_resp.status_code,
            loc, ok_human)

        self.out.warn(info)
        self.out.fatal('It is possible that the website is not running %s. If you disagree, please specify a --method.' %
                self._meta.label)

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

    def enumerate(self, url, base_url_supplied, scanning_method, iterator_returning_method, max_iterator=500, threads=10, verb='head'):
        '''
            @param url base URL for the website.
            @param base_url_supplied Base url for themes, plugins. E.g. '%ssites/all/modules/%s/'
            @param scanning_method see ScanningMethod
            @param iterator_returning_method a function which returns an
                element that, when iterated, will return a full list of plugins
            @param max_iterator integer that will be passed unto iterator_returning_method
            @param threads number of threads
            @param verb what HTTP verb. Valid options are 'get' and 'head'.
        '''
        if common.is_string(base_url_supplied):
            base_urls = [base_url_supplied]
        else:
            base_urls = base_url_supplied

        sess_verb = getattr(self.session, verb)
        futures = []
        with ThreadPoolExecutor(max_workers=threads) as executor:
            for base_url in base_urls:
                plugins = iterator_returning_method(max_iterator)

                if scanning_method == ScanningMethod.not_found:
                    url_template = base_url + self.module_readme_file
                    expected_status = 200
                else:
                    url_template = base_url
                    expected_status = common.scan_http_status(scanning_method)

                for plugin_name in plugins:
                    plugin_url = url_template % (url, plugin_name)
                    future = executor.submit(sess_verb, plugin_url)
                    futures.append({
                        'base_url': base_url,
                        'future': future,
                        'plugin_name': plugin_name,
                        'plugin_url': plugin_url,
                    })

            p = ProgressBar(sys.stderr)
            items_progressed = 0
            items_total = len(base_urls) * int(max_iterator)

            no_results = True
            found = []
            for future_array in futures:
                items_progressed += 1
                p.set(items_progressed, items_total)
                r = future_array['future'].result()
                if r.status_code == expected_status:
                    plugin_url = future_array['plugin_url']
                    plugin_name = future_array['plugin_name']

                    no_results = False
                    found.append({
                        'name': plugin_name,
                        'url': plugin_url
                    })
                elif r.status_code >= 500:
                    self.out.warn('Got a 500 error. Is the server overloaded?')

            p.hide()

        return found, no_results

    def enumerate_plugins(self, url, base_url, scanning_method='forbidden', max_plugins=500, threads=10, verb='head'):
        iterator = getattr(self, 'plugins_get')
        return self.enumerate(url, base_url, scanning_method, iterator,
                max_plugins, threads, verb)

    def enumerate_themes(self, url, base_url, scanning_method='forbidden', max_plugins=500, threads=10, verb='head'):
        iterator = getattr(self, 'themes_get')
        return self.enumerate(url, base_url, scanning_method, iterator,
                max_plugins, threads, verb)

    def enumerate_interesting(self, url, interesting_urls, threads=10, verb='head'):
        requests_verb = getattr(self.session, verb)

        found = []
        for path, description in interesting_urls:
            interesting_url = url + path
            resp = requests_verb(interesting_url)
            if resp.status_code == 200 or resp.status_code == 301:
                found.append({
                    'url': interesting_url,
                    'description': description,
                })

        return found, len(found) == 0

    def enumerate_version(self, url, versions_file, threads=10, verb='head'):
        requests_verb = getattr(self.session, verb)

        vf = VersionsFile(versions_file)

        hashes = {}
        futures = {}
        files = vf.files_get()
        with ThreadPoolExecutor(max_workers=threads) as executor:
            for file_url in files:
                futures[file_url] = executor.submit(self.enumerate_file_hash,
                        url, file_url=file_url)

            for file_url in futures:
                hashes[file_url] = futures[file_url].result()

        version = vf.version_get(hashes)

        return version, len(version) == 0

    def enumerate_file_hash(self, url, file_url):
        r = self.session.get(url + file_url)
        return hashlib.md5(r.content).hexdigest()

class BasePlugin(BasePluginInternal):
    '''
        For documentation regarding these variables, please see
        example.py
    '''
    folder_url = None
    regular_file_url = None

    plugins_base_url = None
    plugins_file = None
    module_readme_file = None
    themes_base_url = None
    themes_file = None

    versions_file = None

    interesting_urls = None

    can_enumerate_plugins = True
    can_enumerate_themes = True
    can_enumerate_interesting = True
    can_enumerate_version = True

class HumanBasePlugin(controller.CementBaseController):

    def error(self, msg):
        #'red': '\033[91m',
        #'endc': '\033[0m',
        raise RuntimeError('\033[91m%s\033[0m' % msg)

    def prepend_to_file(self, filename, prepend_text):
        f = open(filename,'r')
        temp = f.read()
        f.close()

        f = open(filename, 'w')
        f.write(prepend_text)

        f.write(temp)
        f.close()

    def confirm(self, question):
        sys.stdout.write('%s [y/n]\n' % question)
        while True:
            try:
                return strtobool(raw_input().lower())
            except ValueError:
                sys.stdout.write('Please respond with \'y\' or \'n\'.\n')

    def get_input(self, question):
        print question,
        return raw_input()
