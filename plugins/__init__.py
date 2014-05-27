from cement.core import handler, controller
from enum import Enum
import common
import requests

class BasePlugin(controller.CementBaseController):

    valid_enumerate = ['u', 'p', 't']
    class ScanningMethod(Enum):
        not_found = 1
        forbidden = 2
        ok = 3

    class Meta:
        label = 'baseplugin'
        stacked_on = 'base'

        arguments = []

    def enumerate_route(self):
        url, enumerate = self.app.pargs.url, self.app.pargs.enumerate
        method = self.app.pargs.method

        common.validate_url(url)
        common.validate_enumerate(enumerate, self.valid_enumerate)

        if method:
            scanning_method = common.validate_method(method, self.ScanningMethod)
        else:
            scanning_method = self.determine_scanning_method(url)

        if enumerate == "p":
            finds = self.enumerate_plugins(url, scanning_method)
            noun = "plugins"
        elif enumerate == "u":
            self.enumerate_users(url, scanning_method)
        elif enumerate == "t":
            self.enumerate_themes(url, scanning_method)

        print common.template("common/list_noun.tpl", {"noun":noun,
            "items":finds, "empty":len(finds) == 0, "Noun":noun.capitalize()})

    def determine_scanning_method(self, url):
        folder_resp = requests.get(url + self.folder_url)
        ok_resp = requests.get(url + self.regular_file_url)

        if folder_resp.status_code == 403 and ok_resp.status_code == 200:
            return self.ScanningMethod.forbidden
        else:
            raise RuntimeError("""It is possible that the website is not running
                    %s. If you want to override this, specify a --method.""" %
                    "")

    def enumerate_plugins(self, url, scanning_method):
        common.echo("Scanning...")
        plugins = self.plugins_get()
        found_plugins = []
        for plugin in plugins:
            r = requests.get(self.base_url % (url, plugin))
            if r.status_code == 403:
                found_plugins.append(plugin)

        return found_plugins

    def enumerate_users(self, url):
        raise NotImplementedError("Not implemented yet.")

    def enumerate_themes(self, url):
        raise NotImplementedError("Not implemented yet.")
