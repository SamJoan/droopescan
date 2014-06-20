#!/usr/bin/python
"""
    |
 ___| ___  ___  ___  ___  ___  ___  ___  ___  ___
|   )|   )|   )|   )|   )|___)|___ |    |   )|   )
|__/ |    |__/ |__/ |__/ |__   __/ |__  |__/||  /
                    |
=================================================
"""
from cement.core import backend, foundation, controller, handler
from cement.utils.misc import init_defaults
from plugins import Verb, ScanningMethod, Enumerate
from common import template, enum_list
import common

class DroopeScanBase(controller.CementBaseController):
    class Meta:
        label = 'base'
        description = __doc__

        argument_formatter = common.SmartFormatter

        epilog = template("help_epilog.tpl")

        arguments = [
                (['--url'], dict(action='store', help='', required=True)),
                (['--enumerate', '-e'], dict(action='store', help='R|' +
                    template("help_enumerate.tpl"),
                    choices=enum_list(Enumerate), default="a")),
                (['--method'], dict(action='store', help="R|" +
                    template("help_method.tpl"), choices=enum_list(ScanningMethod))),
                (['--number', '-n'], dict(action='store', help="""Number of
                    words to attempt from the plugin/theme dictionary. Default
                    is 1000. Use -n 'all' to use all available..""", default=1000)),
                (['--plugins-base-url'], dict(action='store', help="""Location
                    where the plugins are stored by the CMS. Default is the CMS'
                    default location. First %%s in string will be replaced with
                    the url, and the second one will be replaced with the module
                    name. E.g. '%%ssites/all/modules/%%s/'""")),
                (['--themes-base-url'], dict(action='store', help="""Same as
                    above, but for themes.""")),
                (['--threads', '-t'], dict(action='store', help="""Number of
                    threads.""", default=10)),
                (['--verb'], dict(action='store', help="""The HTTP verb to use;
                the default option is head, except for version enumeration
                requests, which are always get for obvious reasons""",
                default='head', choices=enum_list(Verb))),
            ]

    @controller.expose(hide=True)
    def default(self):
        raise RuntimeError(self.app.args.format_help())

class DroopeScan(foundation.CementApp):
    testing = False
    class Meta:
        label = 'droopescan'
        base_controller = DroopeScanBase

if __name__ == "__main__":
    ds = DroopeScan("DroopeScan",
            plugin_config_dir="./plugins.d",
            plugin_dir="./plugins")

    try:
        ds.setup()
        ds.run()
    except RuntimeError as e:
        if not ds.debug and not ds.testing:
            print(e)
        else:
            raise
    finally:
        ds.close()

