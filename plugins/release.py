from cement.core import handler, controller
from common import template
from common.plugins_util import Plugin, plugins_get
from distutils.util import strtobool
from subprocess import call
import sys, tempfile, os

CHANGELOG = 'CHANGELOG'

class Release(controller.CementBaseController):

    test_runs_base = ['./droopescan']

    test_runs_append = ['-n', '100', '-t', '4']

    test_runs = [
            ['scan', 'drupal', '--url', 'https://www.drupal.org'],
            ['scan', 'silverstripe', '--url', 'http://demo.silverstripe.org'],
            ['scan', 'dnn', '--url', 'http://www.dnnsoftware.com'],
        ]

    class Meta:
        label = 'release'

    def confirm(self, question):
        sys.stdout.write('%s [y/n]\n' % question)
        while True:
            try:
                return strtobool(raw_input().lower())
            except ValueError:
                sys.stdout.write('Please respond with \'y\' or \'n\'.\n')

    def get_input(self, question):
        print question,
        return raw_input()

    def read_first_line(self, file):
        with open(file, 'r') as f:
          first_line = f.readline()

        return first_line.strip()

    def changelog(self, version):
        header = '%s\n%s\n\n' % (version, ('='*len(version)))
        with tempfile.NamedTemporaryFile(suffix=".tmp") as temp:
          temp.write(header)
          temp.flush()
          call(['vim', temp.name])

          return header + temp.read() + "\n"

    def scan_external(self):
        all_ok = True
        for run in self.test_runs:
            args = self.test_runs_base + run + self.test_runs_append
            print args
            ret_code = call(args)
            if ret_code != 0:
                all_ok = False
                break
            else:
                print "OK"

        return all_ok

    def error(self, msg):
        #'red': '\033[91m',
        #'endc': '\033[0m',
        print '\033[91m%s\033[0m' % msg

    def prepend_to_file(self, filename, prepend_text):
        f = open(filename,'r')
        temp = f.read()
        f.close()

        f = open(filename, 'w')
        f.write(prepend_text)

        f.write(temp)
        f.close()

    @controller.expose(help='', hide=True)
    def release(self):
        # internal sanity checks.
        tests_passed = call(['nosetests']) == 0
        if not tests_passed:
            self.error("Unit tests failed... abort.")
            return

        external_passed = self.scan_external()
        if not external_passed:
            self.error("External scans failed... abort.")
            return

        human_approves = self.confirm("Does that look OK for you?")

        if human_approves:
            prev_version_nb = self.read_first_line(CHANGELOG)
            version_nb = self.get_input("Version number (prev %s):" %
                    prev_version_nb)

            final = self.changelog(version_nb)

            print "The following will be prepended to the CHANGELOG:\n---\n%s---" % final

            ok = self.confirm("Is that OK?")
            if ok:
                self.prepend_to_file(CHANGELOG, final)
            else:
                self.error('Canceled by user')

        else:
            self.error('Canceled by user.')

def load():
    handler.register(Release)

