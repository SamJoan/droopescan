#!/usr/bin/env python

from __future__ import print_function
from cement.core import backend, foundation, controller, handler
from cement import Controller, App, ex
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

class DroopeScanBase(Controller):
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

    @ex(hide=True)
    def default(self):
        print(template("intro.mustache", {'version': version_get(),
            'color': True}))

class DroopeScan(App):
    testing = False
    class Meta:
        label = 'droopescan'
        base_controller = DroopeScanBase
        exit_on_close = False
        #framework_logging = False
        config_dirs = [dscan.PWD + "./plugins.d"]
        plugin_dirs = [dscan.PWD + "./plugins"]
        plugins = [
            'drupal',
            'wordpress',
            'joomla',
            'moodle',
            'silverstripe',
            'example',
            'stats',
            'release',
            'tests',
            'update',
        ]

def reorder_argv_for_backward_compatibility(argv):
    """
    Reorder command line arguments for backward compatibility with Cement 2.x.
    Converts: scan drupal -u URL -e v
    To:       scan -u URL -e v drupal

    This allows both old and new argument orders to work.
    Also adds 'default' subcommand when no CMS is specified for CMS identification.
    """
    if len(argv) < 3:
        return argv

    # Check if we're using the scan command
    if 'scan' not in argv:
        return argv

    scan_idx = argv.index('scan')
    if scan_idx >= len(argv) - 1:
        return argv

    # List of CMS subcommands
    cms_commands = ['drupal', 'wordpress', 'wp', 'joomla', 'moodle',
                    'silverstripe', 'ss', 'example', 'default']

    # Check if the next argument after 'scan' is a CMS command
    next_arg = argv[scan_idx + 1]
    if next_arg not in cms_commands:
        # New format (scan -u URL ...) without CMS specified
        # Check if any CMS command exists anywhere in argv
        has_cms_command = any(arg in cms_commands for arg in argv[scan_idx + 1:])

        if not has_cms_command:
            # No CMS specified - add 'default' at the end for CMS identification
            return argv + ['default']
        else:
            # CMS command exists later in the argument list (already in new format)
            return argv

    # Old format detected (scan cms -u URL ...)
    # Find where the CMS command is and where options start
    cms_idx = scan_idx + 1
    cms_name = argv[cms_idx]

    # Collect all arguments after the CMS name (these are the options)
    options = argv[cms_idx + 1:]

    # Rebuild: [program, ...before_scan, 'scan', *options, cms_name, ...after]
    new_argv = argv[:scan_idx + 1] + options + [cms_name]

    return new_argv

def main():
    # Print help when no arguments are provided
    if len(sys.argv) == 1:
        sys.argv.append('--help')

    # Reorder argv for backward compatibility with Cement 2.x argument order
    sys.argv = reorder_argv_for_backward_compatibility(sys.argv)

    ds = DroopeScan("DroopeScan", catch_signals=None)

    ds.handler.register(Scan)

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

