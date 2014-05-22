#!/usr/bin/python
from cement.core import backend, foundation, controller, handler
import common

class DroopeScanBase(controller.CementBaseController):
    class Meta:
        label = 'base'
        description = "A general purpose CMS scanner (which only scans drupal)"

        config_defaults = dict(
            url='bar',
            some_other_option='my default value',
            )

        arguments = [
                (['--url'], dict(action='store', help='')),
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
    except Exception as e:
        if not ds.debug and not ds.testing:
            print(e)
        else:
            raise
    finally:
        ds.close()

