from __future__ import print_function
from cement.core import controller
from common.functions import template
from common import template
from plugins.internal.base_plugin import BasePlugin
from plugins.internal.base_plugin_internal import BasePluginInternal
import common
import common.functions as f
import common.plugins_util as pu
import common.versions as v

class Scan(BasePlugin):

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
                (['--threads', '-t'], dict(action='store', help='''Number of
                    threads. Default 4.''', default=4, type=int)),
                (['--number', '-n'], dict(action='store', help='''Number of
                    words to attempt from the plugin/theme dictionary. Default
                    is 1000. Use -n 'all' to use all available.''',
                    default=BasePluginInternal.NUMBER_DEFAULT)),
                (['--output', '-o'], dict(action='store', help='Output format',
                    choices=common.enum_list(common.ValidOutputs), default='standard')),
                (['--debug-requests'], dict(action='store_true', help="""Prints every
                    HTTP request made and the response returned from the server
                    for debugging purposes. Disables threading and loading
                    bars.""", default=False)),
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
                (['--plugins-base-url'], dict(action='store', help="""Location
                    where the plugins are stored by the CMS. Default is the CMS'
                    default location. First %%s in string will be replaced with
                    the url, and the second one will be replaced with the module
                    name. E.g. '%%ssites/all/modules/%%s/'""")),
                (['--themes-base-url'], dict(action='store', help='''Same as
                    above, but for themes.''')),
                (['--error-log'], dict(action='store', help='''A file to store the
                    errors on.''', default='-')),
                (['--timeout'], dict(action='store', help="""How long to wait
                    for an HTTP response before timing out (in seconds).""",
                    default=45, type=int)),
                (['--timeout-host'], dict(action='store', help="""Maximum time
                    to spend per host (in seconds).""", default=1800, type=int)),
                (['--no-follow-redirects'], dict(action='store_false', help="""Prevent
                    the following of redirects.""", dest="follow_redirects", default=True)),
            ]

    @controller.expose(hide=True)
    def default(self):
        plugins = pu.plugins_base_get()
        opts = self._options(self.app.pargs)
        instances = self._instances_get(opts, plugins)

        if 'url_file' in opts:
            i = 0
            with open(opts['url_file']) as url_file:
                to_scan = {}
                for url in url_file:
                    url = url.strip()
                    found = False
                    for cms_name in instances:
                        inst_dict = instances[cms_name]
                        inst = inst_dict['inst']
                        vf = inst_dict['vf']
                        if inst.cms_identify(opts, vf, url) == True:
                            if cms_name not in to_scan:
                                to_scan[cms_name] = []

                            url = f.repair_url(url, self.out)
                            to_scan[cms_name].append(url)
                            found = True
                            break

                    if not found:
                        inst.out.warn("'%s' not identified as being a CMS we support." % url)

                    if i % 1000 == 0 and i != 0:
                       self._process_identify(opts, instances, to_scan)
                       to_scan = {}

                    i += 1

                if to_scan:
                    self._process_identify(opts, instances, to_scan)

        else:
           for cms_name in instances:
               inst_dict = instances[cms_name]
               inst = inst_dict['inst']
               vf = inst_dict['vf']

               url = f.repair_url(opts['url'], self.out)

               if inst.cms_identify(opts, vf, url) == True:
                   inst.out.echo(template("enumerate_cms.mustache",
                       {"cms_name": cms_name}))
                   inst.process_url(opts, **inst_dict['kwargs'])

    def _process_identify(self, opts, instances, to_scan):
        for cms_name in to_scan:
            inst_dict = instances[cms_name]
            cms_urls = to_scan[cms_name]
            inst = inst_dict['inst']
            del inst_dict['kwargs']['hide_progressbar']
            if len(cms_urls) > 0:
                inst.process_url_iterable(cms_urls, opts, **inst_dict['kwargs'])

    def _instances_get(self, opts, plugins):
        instances = {}
        for plugin in plugins:
            inst = plugin()
            hp, func, enabled_func = inst._general_init(opts)
            name = inst._meta.label
            vf = v.VersionsFile(inst.versions_file)

            instances[name] = {
                'inst': inst,
                'vf': vf,
                'kwargs': {
                    'hide_progressbar': hp,
                    'functionality': func,
                    'enabled_functionality': enabled_func
                }
            }

        return instances

