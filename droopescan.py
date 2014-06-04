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
import common

class DroopeScanBase(controller.CementBaseController):
    class Meta:
        label = 'base'
        description = __doc__

        config_defaults = dict(
            url='bar',
            some_other_option='my default value',
            )

        arguments = [
                (['--url'], dict(action='store', help='')),
                (['--enumerate', '-e'], dict(action='store',
                help="""What to enumerate. Available options are u, p and t. These
                    ennumerate users, plugins and themes respectively.""")),
                (['--method'], dict(action='store', help="""Some webservers
                    respond with 403 when a folder exists. Others with a 404.
                    Others with a 200. Valid options are [forbidden, not_found,
                        ok]. Default is to determine.""")),
                (['--plugins-base-url'], dict(action='store', help="""Location
                    where the plugins are stored by the CMS. Default is the CMS'
                    default location. First %%s in string will be replaced with
                    the url, and the second one will be replaced with the module
                    name. E.g. '%%ssites/all/modules/%%s/'""")),
                (['--themes-base-url'], dict(action='store', help="""Same as
                    above, but for themes.""")),
                (['--number', '-n'], dict(action='store', help="""Number of
                    words to attempt from the plugin/theme dictionary. Default
                    is top 500.""")),
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
    # create the app
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

