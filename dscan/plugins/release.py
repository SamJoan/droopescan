from cement.core import handler, controller
from common import template
from common.plugins_util import Plugin, plugins_get
from distutils.util import strtobool
from plugins import HumanBasePlugin
from subprocess import call
import re
import sys, tempfile, os

CHANGELOG = '../CHANGELOG'

def c(*args, **kwargs):
    ret = call(*args, **kwargs)
    if ret != 0:
        raise RuntimeError("Command %s failed." % args[0])

    return ret

class Release(HumanBasePlugin):

    test_runs_base = ['../droopescan']

    test_runs_append = ['-n', '100', '-t', '4']

    test_runs = [
            ['scan', 'drupal', '--url', 'https://www.drupal.org'],
            ['scan', 'silverstripe', '--url', 'http://demo.silverstripe.org'],
        ]

    class Meta:
        label = 'release'
        hide = True
        stacked_on = 'base'
        stacked_type = 'nested'
        arguments = [
            (['-s', '--skip-external'], dict(action='store_true', help='Skip external tests.',
                required=False, default=False)),
        ]

    def read_first_line(self, file):
        with open(file, 'r') as f:
          first_line = f.readline()

        return first_line.strip()

    def changelog(self, version):
        header = '%s\n%s\n\n*' % (version, ('='*len(version)))
        with tempfile.NamedTemporaryFile(suffix=".tmp") as temp:
          temp.write(header)
          temp.flush()
          call(['vim', temp.name])

          return header + temp.read() + "\n"

    def scan_external(self):
        all_ok = True
        for run in self.test_runs:
            args = self.test_runs_base + run + self.test_runs_append
            print(args)
            ret_code = call(args)
            if ret_code != 0:
                all_ok = False
                break
            else:
                print("OK")

        return all_ok

    @controller.expose(help='', hide=True)
    def default(self):
        skip_external = self.app.pargs.skip_external

        tests_passed = call(['../droopescan', 'test']) == 0
        if not tests_passed:
            self.error("Unit tests failed... abort.")
            return

        if not skip_external:
            external_passed = self.scan_external()
            if not external_passed:
                self.error("External scans failed... abort.")
                return

        human_approves = self.confirm("Does that look OK for you?")
        if human_approves:
            prev_version_nb = self.read_first_line(CHANGELOG)
            version_nb = self.get_input("Version number (prev %s):" %
                    prev_version_nb)

            final = self.changelog(version_nb).strip() + "\n\n"

            print("The following will be prepended to the CHANGELOG:\n---\n%s---" % final)

            ok = self.confirm("Is that OK?")
            if ok:
                self.prepend_to_file(CHANGELOG, final)

                try:
                    c(['git', 'add', '..'])
                    c(['git', 'commit', '-m', 'Tagging version \'%s\'' %
                        version_nb])

                    c(['git', 'checkout', 'master'])
                    c(['git', 'merge', 'development'])

                    c(['git', 'tag', version_nb])
                    call('git remote | xargs -l git push --all', shell=True)
                    call('git remote | xargs -l git push --tags', shell=True)

                    is_final_release = '^[0-9.]*$'
                    if re.match(is_final_release, version_nb):
                        pypi_repo = 'pypi'
                    else:
                        pypi_repo = 'test'

                    c(['git', 'clean', '-dXnff'])
                    ok = self.confirm("Is that OK?")
                    if ok:
                        c(['git', 'clean', '-dXff'])
                        c(['python', 'setup.py', 'sdist', 'upload', '-r',
                            pypi_repo], cwd='..')
                        c(['python', 'setup.py', 'bdist_wheel', 'upload', '-r',
                            pypi_repo], cwd='..')
                    else:
                        self.error('Can\'t clean. Perform release manually.')

                finally:
                    c(['git', 'checkout', 'development'])

            else:
                self.error('Canceled by user')

        else:
            self.error('Canceled by user.')

def load():
    handler.register(Release)

