from __future__ import print_function
from cement.core import handler, controller
from distutils.util import strtobool
import common.functions
import sys

class HumanBasePlugin(controller.CementBaseController):

    def error(self, *args, **kwargs):
        common.functions.error(*args, **kwargs)

    def msg(self, msg, end='\n'):
        print(msg, end=end)

    def prepend_to_file(self, filename, prepend_text):
        f = open(filename,'r')
        temp = f.read()
        f.close()

        f = open(filename, 'w')
        f.write(prepend_text)

        f.write(temp)
        f.close()

    def get_input(self, question):
        print(question, end=' ')
        return raw_input()
