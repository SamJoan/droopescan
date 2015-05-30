#!/usr/bin/env python

from __future__ import print_function
from cement.core import backend, foundation, controller, handler
from cement.utils.misc import init_defaults
from common.functions import template, version_get
from plugins import Scan
import common, sys, signal
import droopescan
import os

class DroopeScanBase(controller.CementBaseController):
    class Meta:
        label = 'base'
        description = """
    |
 ___| ___  ___  ___  ___  ___  ___  ___  ___  ___
|   )|   )|   )|   )|   )|___)|___ |    |   )|   )
|__/ |    |__/ |__/ |__/ |__   __/ |__  |__/||  /
                    |
=================================================
"""

        epilog = template("help_epilog.mustache")

    @controller.expose(hide=True)
    def default(self):
        print(template("intro.mustache", {'version': version_get(),
            'color': True}))

class DroopeScan(foundation.CementApp):
    testing = False
    class Meta:
        label = 'droopescan'
        base_controller = DroopeScanBase
        exit_on_close = False

def main(pwd):
    defaults = init_defaults('DroopeScan', 'general')
    defaults['general']['pwd'] = pwd

    ds = DroopeScan("DroopeScan", plugin_config_dir="./plugins.d",
            plugin_dir="./plugins", catch_signals=None,
            config_defaults=defaults)

    handler.register(Scan)

    try:
        ds.setup()
        ds.run()
    except RuntimeError as e:
        if not ds.debug and not ds.testing:
            print(e, file=sys.stdout)
        else:
            raise
    finally:
        ds.close()

