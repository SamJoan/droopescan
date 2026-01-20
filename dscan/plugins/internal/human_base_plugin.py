from __future__ import print_function
from cement.core import handler, controller
from cement import Controller
import dscan.common.functions as f
import sys

class HumanBasePlugin(Controller):
    def error(self, *args, **kwargs):
        f.error(*args, **kwargs)

    def msg(self, msg, end='\n'):
        print(msg, end=end)
