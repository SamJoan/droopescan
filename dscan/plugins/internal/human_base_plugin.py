from __future__ import print_function
from cement.core import handler, controller
import dscan.common.functions as f
import sys

class HumanBasePlugin(controller.CementBaseController):
    def error(self, *args, **kwargs):
        f.error(*args, **kwargs)

    def msg(self, msg, end='\n'):
        print(msg, end=end)
