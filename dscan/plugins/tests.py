from cement.core import handler, controller
from plugins import HumanBasePlugin
from subprocess import call
import os, sys

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
        ]

    @controller.expose(help='', hide=True)
    def default(self):
        env = {'PYTHONPATH': os.getcwd()}
        single_test = self.app.pargs.single_test
        if not single_test:
            call(['python2', '/usr/local/bin/nosetests'], env=env)
            call(['python3', '/usr/local/bin/nosetests'], env=env)
        else:
            test_file = recursive_grep('tests/', single_test)
            if test_file:
                self.msg('Test found on file "%s".' % test_file)
            else:
                self.error('No test found with name "%s"' % single_test)

            appendix = 'tests.py'
            tna = test_file[0:-1 * len(appendix) - 1].split('_')
            underscore = '_'.join(tna)
            upper = "".join(w.capitalize() for w in tna)

            test = 'tests.%s_tests:%sTests.%s' % (underscore, upper, single_test)

            call(['python', '/usr/local/bin/nosetests', '--nocapture', test], env=env)

def load():
    handler.register(Tests)

