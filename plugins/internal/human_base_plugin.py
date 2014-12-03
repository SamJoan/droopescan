from __future__ import print_function
from cement.core import handler, controller
from distutils.util import strtobool
import sys

class HumanBasePlugin(controller.CementBaseController):

    def error(self, msg):
        #'red': '\033[91m',
        #'endc': '\033[0m',
        raise RuntimeError('\033[91m%s\033[0m' % msg)

    def msg(self, msg):
        print(msg)

    def prepend_to_file(self, filename, prepend_text):
        f = open(filename,'r')
        temp = f.read()
        f.close()

        f = open(filename, 'w')
        f.write(prepend_text)

        f.write(temp)
        f.close()

    def confirm(self, question):
        sys.stdout.write('%s [y/n]\n' % question)
        while True:
            try:
                user_input = raw_input().lower()
                return strtobool(user_input)
            except ValueError:
                sys.stdout.write('Please respond with \'y\' or \'n\'.\n')

    def get_input(self, question):
        print(question, end=' ')
        return raw_input()
