from __future__ import print_function
from dscan.plugins.internal.base_plugin_internal import BasePluginInternal
import dscan

class BasePlugin(BasePluginInternal):
    '''
        For documentation regarding these variables, please see
        example.py
    '''
    forbidden_url = None
    regular_file_url = None

    plugins_base_url = None
    plugins_file = None
    module_common_file = None
    themes_base_url = None
    themes_file = None

    versions_file = None

    interesting_urls = None

    can_enumerate_plugins = True
    can_enumerate_themes = True
    can_enumerate_interesting = True
    can_enumerate_version = True

    def __init__(self):
        super(BasePlugin, self).__init__()

        label = self._meta.label
        self.plugins_file = dscan.PWD + "plugins/%s/plugins.txt" % label
        self.themes_file = dscan.PWD + "plugins/%s/themes.txt" % label
        self.versions_file = dscan.PWD + "plugins/%s/versions.xml" % label

