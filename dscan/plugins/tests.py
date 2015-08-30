from cement.core import handler, controller
from dscan.plugins import HumanBasePlugin
from subprocess import call
import os, sys, dscan

BASE_FOLDER = '/var/www/drupal/'
UPDATE_MAJOR = ['6', '7']

def recursive_grep(directory, needle):
    return_file = None
    for f in os.listdir(directory):
        if f.endswith('.py'):
            with open(directory + f, 'r') as fh:
                for line in fh:
                    if needle in line:
                        return_file = f

            if return_file:
                break

    return return_file

class Tests(HumanBasePlugin):
    class Meta:
        label = 'test'
        stacked_on = 'base'
        stacked_type = 'nested'
        hide = True
        arguments = [
            (['-s', '--single-test'], dict(action='store', help='Name of test to run',
                required=False, default=None)),
            (['-3', '--just-three'], dict(action='store_true', help='Just run python 3 tests.',
                required=False, default=None)),
            (['-2', '--just-two'], dict(action='store_true', help='Just run python 3 tests.',
                required=False, default=None)),
            (['-c', '--with-coverage'], dict(action='store_true', help='Do test coverage',
                required=False, default=False)),
        ]

    @controller.expose(help='', hide=True)
    def default(self):
        env = {}
        single_test = self.app.pargs.single_test
        with_coverage = self.app.pargs.with_coverage
        just_three = self.app.pargs.just_three
        just_two = self.app.pargs.just_two

        if single_test and with_coverage:
            self.error('Cannot run with both -c and -s.')

        exit = 0
        if not single_test:
            call_base = ['/usr/local/bin/nosetests', '--exclude=async']

            if with_coverage:
                call_base += ['--with-coverage', '--cover-package', 'dscan',
                        '--cover-inclusive', '--cover-html']

            if not just_three:
                e1 = call(['python2'] + call_base, env=env)
            else:
                e1 = 0

            if not just_two:
                e2 = call(['python3'] + call_base, env=env)
            else:
                e2 = 0

            if e1 != 0 or e2 != 0:
                exit = 1

        else:
            test_file = recursive_grep(dscan.PWD + 'tests/', single_test + "(")
            if not test_file:
                self.error('No test found with name "%s"' % single_test)

            appendix = 'tests.py'
            tna = test_file[0:-1 * len(appendix) - 1].split('_')
            underscore = '_'.join(tna)
            upper = "".join(w.capitalize() for w in tna)

            test = 'dscan.tests.%s_tests:%sTests.%s' % (underscore, upper, single_test)

            if just_two:
                exit = call(['python2', '/usr/local/bin/nosetests', '--nocapture', test], env=env)
            else:
                exit = call(['python3', '/usr/local/bin/nosetests', '--nocapture', test], env=env)

        sys.exit(exit)

def load(app=None):
    handler.register(Tests)

