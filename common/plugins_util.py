from cement.core import handler
from plugins import BasePlugin
from common import file_len

def plugins_get():
    controllers = handler.list('controller')
    plugins = filter(lambda c: issubclass(c, BasePlugin), controllers)

    return_plugins = []
    for p in plugins:
        plugin = Plugin(p)
        return_plugins.append(plugin)

    return return_plugins

class Plugin():

    plugins_can_enumerate = False
    plugins_wordlist_size = None

    themes_can_enumerate = False
    themes_wordlist_size = None

    interesting_can_enumerate = False
    interesting_urls_size = None

    version_can_enumerate = False
    version_highest_known = None

    def __init__(self, plugin=None):
        """
            @param plugin as returned by handler.list('controller'). Must
                extend BasePlugin.
        """
        if plugin:
            if plugin.can_enumerate_plugins:
                self.plugins_can_enumerate = True
                self.plugins_wordlist_size = file_len(plugin.plugins_file)



