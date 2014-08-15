from cement.core import handler, controller
from plugins import HumanBasePlugin
from subprocess import call

BASE_FOLDER = '/var/www/drupal/'
UPDATE_MAJOR = ['6', '7']

class Tests(HumanBasePlugin):
    class Meta:
        label = 'test'
        stacked_on = 'base'
        stacked_type = 'nested'
        hide = True

        arguments = [
                (['--integration', '-i'], dict(action='store_true', help='')),
            ]

    @controller.expose(help='', hide=True)
    def default(self):
        integration = self.app.pargs.integration
        if integration:
            call(['nosetests'])
        else:
            call(['nosetests', '--exclude', 'integration_tests'])

def load():
    handler.register(Tests)

