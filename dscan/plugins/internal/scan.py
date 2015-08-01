from __future__ import print_function
from cement.core import controller
from collections import OrderedDict
from common.functions import template
from common import template
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from plugins.internal.base_plugin import BasePlugin
from plugins.internal.base_plugin_internal import BasePluginInternal
import common
import common.functions as f
import common.plugins_util as pu
import common.versions as v
import sys
import traceback

class Scan(BasePlugin):

    IDENTIFY_BATCH_SIZE = 1000

    class Meta:
        label = 'scan'
        description = 'cms scanning functionality.'
        stacked_on = 'base'
        stacked_type = 'nested'

        epilog = "\n"

        argument_formatter = common.SmartFormatter
        epilog = template("help_epilog.mustache")

        arguments = [
                (['-u', '--url'], dict(action='store', help='')),
                (['-U', '--url-file'], dict(action='store', help='''A file which
                    contains a list of URLs.''')),

                (['--enumerate', '-e'], dict(action='store', help='R|' +
                    common.template('help_enumerate.mustache'),
                    choices=common.enum_list(common.Enumerate), default='a')),
                (['--method'], dict(action='store', help='R|' +
                    common.template('help_method.mustache'), choices=common.enum_list(common.ScanningMethod))),
                (['--verb'], dict(action='store', help="""The HTTP verb to use;
                    the default option is head, except for version enumeration
                    requests, which are always get because we need to get the hash
                    from the file's contents""", default='head',
                    choices=common.enum_list(common.Verb))),
                (['--number', '-n'], dict(action='store', help='''Number of
                    words to attempt from the plugin/theme dictionary. Default
                    is 1000. Use -n 'all' to use all available.''',
                    default=BasePluginInternal.NUMBER_DEFAULT)),
                (['--plugins-base-url'], dict(action='store', help="""Location
                    where the plugins are stored by the CMS. Default is the CMS'
                    default location. First %%s in string will be replaced with
                    the url, and the second one will be replaced with the module
                    name. E.g. '%%ssites/all/modules/%%s/'""")),
                (['--themes-base-url'], dict(action='store', help='''Same as
                    above, but for themes.''')),
                (['--timeout'], dict(action='store', help="""How long to wait
                    for an HTTP response before timing out (in seconds).""",
                    default=45, type=int)),
                (['--timeout-host'], dict(action='store', help="""Maximum time
                    to spend per host (in seconds).""", default=1800, type=int)),
                (['--no-follow-redirects'], dict(action='store_false', help="""Prevent
                    the following of redirects.""", dest="follow_redirects", default=True)),
                (['--host'], dict(action='store', help="""Override host header
                    with this value.""", default=None)),
                (['--massscan-override'], dict(action='store_true',
                    help="""Overrides defaults with defaults convenient for
                    mass-scanning of hosts.""", default=False)),

                (['--threads', '-t'], dict(action='store', help='''Number of
                    threads. Default 4.''', default=4, type=int)),
                (['--threads-identify'], dict(action='store', help='''Number of
                    threads used for CMS identification.''', default=None, type=int)),
                (['--threads-scan'], dict(action='store', help='''Threads used
                    for mass scanning.''', default=None, type=int)),
                (['--threads-enumerate'], dict(action='store', help='''Threads
                    used for plugin enumeration.''', default=None, type=int)),

                (['--output', '-o'], dict(action='store', help='Output format',
                    choices=common.enum_list(common.ValidOutputs), default='standard')),
                (['--debug-requests'], dict(action='store_true', help="""Prints every
                    HTTP request made and the response returned from the server
                    for debugging purposes. Disables threading and loading
                    bars.""", default=False)),
                (['--error-log'], dict(action='store', help='''A file to store the
                    errors on.''', default=None)),
            ]

    @controller.expose(hide=True)
    def default(self):
        plugins = pu.plugins_base_get()
        opts = self._options(self.app.pargs)
        url_file_input = 'url_file' in opts
        self._general_init(opts)
        instances = self._instances_get(opts, plugins, url_file_input)

        follow_redirects = opts['follow_redirects']
        opts['follow_redirects'] = False

        if url_file_input:
            self.out.debug('scan.default -> url_file')
            self._process_scan_url_file(opts['url_file'], follow_redirects)
        else:
            self.out.debug('scan.default -> url')
            url = opts['url']
            if not url:
                self.out.fatal("--url parameter is blank.")

            cms_name, scan_out = self._process_cms_identify(url, opts, instances,
                    follow_redirects)

            url, host_header = scan_out

            inst_dict = instances[cms_name]
            inst = inst_dict['inst']

            opts['url'] = url
            opts['headers'] = self._generate_headers(host_header)

            inst.process_url(opts, **inst_dict['kwargs'])

    def _process_scan_url_file(self, file_location, follow_redirects):
        self.out.debug('scan._process_scan_url_file')
        with open(file_location) as url_file:
            i = 0
            urls = []
            for url in url_file:
                if i % self.IDENTIFY_BATCH_SIZE == 0 and i != 0:
                    plugins = pu.plugins_base_get()
                    opts = self._options(self.app.pargs)
                    executor = ThreadPoolExecutor(max_workers=opts['threads_identify'])
                    instances = self._instances_get(opts, plugins,
                            url_file_input=True)

                    self._process_generate_futures(urls, executor, opts,
                        instances, follow_redirects)

                    executor.shutdown()
                    del executor
                    del plugins
                    del opts
                    del instances
                else:
                    urls.append(url)

                i += 1

            if len(urls) > 0:
                plugins = pu.plugins_base_get()
                opts = self._options(self.app.pargs)
                executor = ThreadPoolExecutor(max_workers=opts['threads_identify'])
                instances = self._instances_get(opts, plugins,
                        url_file_input=True)

                self._process_generate_futures(urls, executor, opts,
                    instances, follow_redirects)

    def _process_generate_futures(self, urls, executor, opts, instances,
            follow_redirects):

        futures = []
        for url in urls:
            url = url.strip()
            future = executor.submit(self._process_cms_identify, url,
                    opts, instances, follow_redirects)

            futures.append({
                'url': url,
                'future': future
            })

        self._process_identify_futures(futures, opts, instances)

    def _process_cms_identify(self, url, opts, instances, follow_redirects):
        self.out.debug('scan._process_cms_identify -> %s' % url)
        try:
            url, host_header = url, opts['headers']['Host']
        except:
            url, host_header = self._process_host_line(url)

        url = f.repair_url(url, self.out)

        if follow_redirects:
            url, host_header = self.determine_redirect(url, host_header, opts)

        found = False
        for cms_name in instances:
            inst_dict = instances[cms_name]
            inst = inst_dict['inst']
            vf = inst_dict['vf']

            if inst.cms_identify(vf, url, opts['timeout'], self._generate_headers(host_header)) == True:
                found = True
                break

        if not found:
            return None, None
        else:
            return cms_name, (url, host_header)

    def _process_identify_futures(self, futures, opts, instances):
        self.out.debug('scan._process_identify_futures')
        to_scan = {}
        for future_dict in futures:
            future = future_dict['future']

            try:
                cms_name, result_tuple = future.result(timeout=opts['timeout_host'])

                if cms_name != None:
                    if cms_name not in to_scan:
                        to_scan[cms_name] = []

                    to_scan[cms_name].append(result_tuple)
            except:
                f.exc_handle(future_dict['url'], self.out, self.app.testing)

        if to_scan:
            self._process_scan(opts, instances, to_scan)
            to_scan = {}

    def _process_scan(self, opts, instances, to_scan):
        self.out.debug('scan._process_scan')
        for cms_name in to_scan:
            inst_dict = instances[cms_name]
            cms_urls = to_scan[cms_name]

            if len(cms_urls) > 0:
                inst_dict['inst'].process_url_iterable(cms_urls, opts, **inst_dict['kwargs'])

    def _instances_get(self, opts, plugins, url_file_input):
        """
        Creates and returns an ordered dictionary containing instances for all available
        scanning plugins, sort of ordered by popularity.
        @param opts: options as returned by self._options.
        @param plugins: plugins as returned by plugins_util.plugins_base_get.
        @param url_file_input: boolean value which indicates whether we are
            scanning an individual URL or a file. This is used to determine
            kwargs required.
        """
        instances = OrderedDict()
        preferred_order = ['wordpress', 'joomla', 'drupal']

        for cms_name in preferred_order:
            for plugin in plugins:
                plugin_name = plugin.__name__.lower()

                if cms_name == plugin_name:
                    instances[plugin_name] = self._instance_get(plugin, opts,
                            url_file_input)

        for plugin in plugins:
            plugin_name = plugin.__name__.lower()
            if plugin_name not in preferred_order:
                instances[plugin_name] = self._instance_get(plugin, opts,
                        url_file_input)

        return instances

    def _instance_get(self, plugin, opts, url_file_input):
        """
        Return an instance dictionary for an individual plugin.
        @see Scan._instances_get.
        """
        inst = plugin()
        hp, func, enabled_func = inst._general_init(opts)
        name = inst._meta.label
        vf = v.VersionsFile(inst.versions_file)

        kwargs = {
            'hide_progressbar': hp,
            'functionality': func,
            'enabled_functionality': enabled_func
        }

        if url_file_input:
            del kwargs['hide_progressbar']

        return {
            'inst': inst,
            'vf': vf,
            'kwargs': kwargs
        }

