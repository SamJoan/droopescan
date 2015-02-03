from __future__ import print_function
from cement.core import controller
from common import template
import common

class Scan(controller.CementBaseController):

    class Meta:
        label = 'scan'
        description = 'cms scanning functionality.'
        stacked_on = 'base'
        stacked_type = 'nested'

        epilog = "\n"

        argument_formatter = common.SmartFormatter
        epilog = template("help_epilog.tpl")

        arguments = [
                (['-u', '--url'], dict(action='store', help='')),
                (['--debug-requests'], dict(action='store_true', help="""Prints every
                    HTTP request made and the response returned from the server
                    for debugging purposes. Disables threading and loading
                    bars.""", default=False)),
                (['--enumerate', '-e'], dict(action='store', help='R|' +
                    common.template('help_enumerate.tpl'),
                    choices=common.enum_list(common.Enumerate), default='a')),
                (['--method'], dict(action='store', help='R|' +
                    common.template('help_method.tpl'), choices=common.enum_list(common.ScanningMethod))),
                (['--threads', '-t'], dict(action='store', help='''Number of
                    threads. Default 4.''', default=4, type=int)),
                (['--number', '-n'], dict(action='store', help='''Number of
                    words to attempt from the plugin/theme dictionary. Default
                    is 1000. Use -n 'all' to use all available.''', default=1000)),
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
                (['-U', '--url-file'], dict(action='store', help='''A file which
                    contains a list of URLs.''')),
                (['--output', '-o'], dict(action='store', help='Output format',
                    choices=common.enum_list(common.ValidOutputs), default='standard')),
                (['--error-log'], dict(action='store', help='''A file to store the
                    errors on.''', default='-')),
                (['--timeout'], dict(action='store', help="""How long to wait
                    for an HTTP response before timing out (in seconds).""",
                    default=15, type=int)),
                (['--timeout-host'], dict(action='store', help="""Maximum time
                    to spend per host (in seconds).""", default=450, type=int)),
                (['--no-follow-redirects'], dict(action='store_false', help="""Prevent
                    the following of redirects.""", dest="follow_redirects", default=True)),
            ]

    @controller.expose(hide=True)
    def default(self):
        raise RuntimeError(self.app.args.format_help())

