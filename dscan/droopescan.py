#!/usr/bin/env python

from __future__ import print_function
from cement.core import backend, foundation, controller, handler
from cement.utils.misc import init_defaults
from dscan.common.functions import template, version_get
from dscan import common
from dscan.plugins import Scan
import dscan
import os
import signal
import sys

def handle_interrupt(signal, stack):
    print("\nShutting down...")
    common.shutdown = True

signal.signal(signal.SIGINT, handle_interrupt)

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
        #framework_logging = False

def main():
    ds = DroopeScan("DroopeScan", plugin_config_dir=dscan.PWD + "./plugins.d",
            plugin_dir=dscan.PWD + "./plugins", catch_signals=None)

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

