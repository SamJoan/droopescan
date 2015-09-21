from __future__ import print_function
from dscan.common.functions import template, strip_whitespace, \
    result_anything_found
from dscan.common.enum import colors
import argparse
import hashlib
import json
import sys
import time

class SmartFormatter(argparse.RawDescriptionHelpFormatter):
    def _split_lines(self, text, width):
        # this is the RawTextHelpFormatter._split_lines
        if text.startswith('R|'):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)

class ProgressBar():
    progress = 0

    def __init__(self, stream, items_total, name):
        self.stream = stream
        self.items_total = items_total
        self.name = name

    def set(self, items_processed, items_total, barLen = 50):
        items_processed = int(items_processed)
        items_total = int(items_total)
        percent = (items_processed * 100) / items_total
        self.stream.write("\r")

        real_percent = percent / 2
        progress = ""
        for i in range(barLen):
            if i < real_percent:
                progress += "="
            else:
                progress += " "

        self.stream.write("%s [ %s ] %d/%d (%d%%)" % (self.name, progress, items_processed, items_total, percent))
        self.stream.flush()

    def increment_progress(self):
        self.progress += 1
        self.set(self.progress, self.items_total)

    def hide(self):
        self.stream.write("\r")
        self.stream.write(" " * 80)
        self.stream.write("\r")

class StandardOutput():

    errors_display = True
    error_log = None
    log_to_file = False
    debug_output = False

    def __init__(self, error_log='-'):
        self.log_to_file = error_log != '-'

        if not self.log_to_file:
            self.error_log = sys.stderr
        else:
            self.errors_display = True
            self.error_log = open(error_log, 'a')

    def close(self):
        if self.log_to_file:
            self.error_log.close()

    def echo(self, msg):
        """
        For miscelaneous messages. E.g. "Initializing scanning".
        """
        self.print(msg)

    def debug(self, msg):
        if self.debug_output:
            self.print(msg)

    def result(self, result, functionality):
        """
        For the final result of the scan.
        @param result: as returned by BasePluginInternal.url_scan
        @param functionality: functionality as returned by
            BasePluginInternal._general_init
        """
        for enumerate in result:

            # The host is a special header, we must not attempt to display it.
            if enumerate == "host" or enumerate == "cms_name":
                continue

            result_ind = result[enumerate]
            finds = result_ind['finds']
            is_empty = result_ind['is_empty']

            template_str = functionality[enumerate]['template']
            template_params = {
                    'noun': enumerate,
                    'Noun': enumerate.capitalize(),
                    'items': finds,
                    'empty': is_empty,
                }

            self.echo(template(template_str, template_params))

    def warn(self, msg, whitespace_strp=True):
        """
        For things that have gone seriously wrong but don't merit a program
        halt.
        Outputs to stderr, so JsonOutput does not need to override.
        @param msg: warning to output.
        @param whitespace_strp: whether to strip whitespace.
        """
        if self.errors_display:
            if whitespace_strp:
                msg = strip_whitespace(msg)

            if not self.log_to_file:
                msg = colors['warn'] + "[+] " + msg + colors['endc']
            else:
                msg = "[" + time.strftime("%c") + "] " + msg

            self.print(msg, file=self.error_log)

    def fatal(self, msg):
        """
        For errors so grave that the program (or thread) cannot continue.
        """
        if not self.log_to_file:
            msg = strip_whitespace(colors['red'] + "[+] " + msg +
                    colors['endc'])
        else:
            msg = "[" + time.strftime("%c") + "] " + msg

        raise RuntimeError(msg)

    def print(self, msg, *args, **kwargs):
        print(msg, *args, **kwargs)

class JsonOutput(StandardOutput):
    errors_display = False

    def echo(self, msg):
        pass

    def result(self, result, functionality=None):
        if result_anything_found(result):
            self.print(json.dumps(result))

class RequestsLogger():

    _session = None

    def __init__(self, session):
        """
        @param session: a requests.Session instance.
        """
        self._session = session

    def _print(self, method, *args, **kwargs):
        """
        Output format affects integration tests.
        @see: IntegrationTests.mock_output
        """
        sess_method = getattr(self._session, method)

        try:
            headers = kwargs['headers']
        except KeyError:
            headers = {}

        tpl = '[%s] %s %s'
        print(tpl % (method, args[0], headers), end=' ')

        try:
            r = sess_method(*args, **kwargs)
        except:
            e = sys.exc_info()
            e_str = "%s: %s" % (e[0], e[1])
            print("FAILED (%s)" % e_str)
            raise

        if method == "get" and r.status_code == 200:
            hsh = hashlib.md5(r.content).hexdigest()
        else:
            hsh = ""

        print(r.status_code, hsh)

        return r

    def head(self, *args, **kwargs):
        return self._print('head', *args, **kwargs)

    def get(self, *args, **kwargs):
        return self._print('get', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self._print('post', *args, **kwargs)

class Output():
    themes = None
    interesting_urls = None
    version = None
    plugins = None
    host = None
