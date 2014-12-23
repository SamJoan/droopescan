from cement.core import handler, controller
from plugins import HumanBasePlugin
from subprocess import call
import os, sys

BASE_FOLDER = '/var/www/drupal/'
UPDATE_MAJOR = ['6', '7']

class Tests(HumanBasePlugin):
    class Meta:
        label = 'test'
        stacked_on = 'base'
        stacked_type = 'nested'
        hide = True

    @controller.expose(help='', hide=True)
    def default(self):
        env = {'PYTHONPATH': os.getcwd()}
        call(['python2', '/usr/local/bin/nosetests'], env=env)
        call(['python3', '/usr/local/bin/nosetests'], env=env)

def load():
    handler.register(Tests)

