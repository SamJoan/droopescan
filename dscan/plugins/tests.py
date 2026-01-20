from cement.core import handler, controller
from cement import ex
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

def which(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return program

class Tests(HumanBasePlugin):
    class Meta:
        label = 'test'
        stacked_on = 'base'
        stacked_type = 'nested'
        arguments = [
            (['-s', '--single-test'], dict(action='store', help='Name of test to run',
                required=False, default=None)),
            (['-c', '--with-coverage'], dict(action='store_true', help='Do test coverage',
                required=False, default=False)),
        ]

    def _default(self):
        self.default()

    @ex(help='Run unit tests')
    def default(self):
        env = {}
        single_test = self.app.pargs.single_test
        with_coverage = self.app.pargs.with_coverage

        if single_test and with_coverage:
            self.error('Cannot run with both -c and -s.')

        nosetests = which('nosetests')
        exit = 0
        if not single_test:
            call_base = [nosetests, '--exclude=async']

            if with_coverage:
                call_base += ['--with-coverage', '--cover-package', 'dscan',
                        '--cover-inclusive', '--cover-html']

            # Run tests using the found nosetests executable
            if call(call_base, env=env) != 0:
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

            exit = call([nosetests, '--nocapture', test], env=env)

        sys.exit(exit)

def load(app=None):
    app.handler.register(Tests)

