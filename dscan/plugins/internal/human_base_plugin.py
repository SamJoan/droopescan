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
