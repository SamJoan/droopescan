from cement.core import handler, controller
from common import logger
from datetime import datetime
import common
import requests

class BasePlugin(controller.CementBaseController):

    valid_enumerate = ['u', 'p', 't']
    class ScanningMethod():
        not_found = 404
        forbidden = 403
        ok = 200

    class Meta:
        label = 'baseplugin'
        stacked_on = 'base'

        arguments = []

    def enumerate_route(self):
        time_start = datetime.now()
        url, enumerate = self.app.pargs.url, self.app.pargs.enumerate
        method = self.app.pargs.method

        pbu = self.app.pargs.plugins_base_url
        plugins_base_url = pbu if pbu else self.plugins_base_url

        tbu = self.app.pargs.themes_base_url
        themes_base_url = tbu if tbu else self.themes_base_url

        url = common.validate_url(url)
        common.validate_enumerate(enumerate, self.valid_enumerate)

        if method:
            scanning_method = common.validate_method(method, self.ScanningMethod)
        else:
            scanning_method = self.determine_scanning_method(url)

        functionality = {}
        if enumerate == "p":
            noun = "plugins"
            functionality[noun] = {
                    "func": getattr(self, "enumerate_plugins"),
                    "base_url": plugins_base_url
                    }
        elif enumerate == "u":
            noun = "users"
            functionality[noun] = {
                    "func": getattr(self, "enumerate_users"),
                    "base_url": None,
                    }
        elif enumerate == "t":
            noun = "themes"
            functionality[noun] = {
                    "func": getattr(self, "enumerate_themes"),
                    "base_url": themes_base_url
                    }

        common.echo(common.template("common/scan_begin.tpl", {"noun": noun, "url": url,
            "plugins_base_url": plugins_base_url, "scanning_method": scanning_method}))

        # The loop of enumeration.
        for enumerate in functionality:
            enum = functionality[enumerate]
            finds = enum["func"](url, enum["base_url"], scanning_method)

            common.echo(common.template("common/list_noun.tpl", {"noun":noun,
                "items":finds, "empty":len(finds) == 0, "Noun":noun.capitalize()}))

        common.echo("[+] Scan finished (%s elapsed)" % str(datetime.now() - time_start))

    def determine_scanning_method(self, url):
        folder_resp = requests.get(url + self.folder_url)
        ok_resp = requests.get(url + self.regular_file_url)

        logger.debug("determine_scanning_method: Server responded with %s and %s for urls %s and %s"
                % (folder_resp.status_code, ok_resp.status_code,
                    self.folder_url, self.regular_file_url))

        if folder_resp.status_code == 403 and ok_resp.status_code == 200:
            return self.ScanningMethod.forbidden
        if folder_resp.status_code == 404 and ok_resp.status_code == 200:
            logger.warning("Known %s folders have returned 404 Not Found. If modules do not have a %s file they will not be detected." %
                    (self._meta.label, self.module_readme_file))
            return self.ScanningMethod.not_found
        if folder_resp.status_code == 200 and ok_resp.status_code == 200:
            logger.warning("""Known folder names for %s are returning 200 OK. Is directory listing enabled?""" % self._meta.label)
            return self.ScanningMethod.ok
        else:
            raise RuntimeError("""It is possible that the website is not running %s. If you disagree, please specify a --method.""" %
                    self._meta.label)

    def plugins_get(self):
        f = open(self.plugins_file)
        for plugin in f:
            yield plugin.strip()

    def themes_get(self):
        f = open(self.themes_file)
        for theme in f:
            yield theme.strip()

    def enumerate(self, url, base_url_supplied, scanning_method, iterator_returning_method):
        """
            @param url base URL for the website.
            @param base_url_supplied Base url for themes, plugins. E.g. '%ssites/all/modules/%s/'
            @param scanning_method see self.ScanningMethod
            @param iterator_returning_method a function which returns an
                element that, when iterated, will return a full list of plugins
        """
        found = []

        if isinstance(base_url_supplied, basestring):
            base_urls = [base_url_supplied]
        else:
            base_urls = base_url_supplied

        for base_url in base_urls:
            plugins = iterator_returning_method()

            if scanning_method == self.ScanningMethod.not_found:
                url_template = base_url + self.module_readme_file
                expected_status = 200
            else:
                url_template = base_url
                expected_status = scanning_method

            for plugin in plugins:
                r = requests.get(url_template % (url, plugin))
                if r.status_code == expected_status:
                    found.append(plugin)

        return found

    def enumerate_plugins(self, url, base_url, scanning_method):
        iterator = getattr(self, "plugins_get")
        return self.enumerate(url, base_url, scanning_method, iterator)

    def enumerate_themes(self, url, base_url, scanning_method):
        iterator = getattr(self, "themes_get")
        return self.enumerate(url, base_url, scanning_method, iterator)

    def enumerate_users(self, url):
        raise NotImplementedError("Not implemented yet.")
