from cement.core import handler, controller
import common

class BasePlugin(controller.CementBaseController):

    valid_enumerate = ['u', 'p', 't']

    class Meta:
        label = 'baseplugin'
        stacked_on = 'base'

        arguments = []

    def enumerate_route(self):
        url, enumerate = self.app.pargs.url, self.app.pargs.enumerate

        common.url_validate(self.app.pargs.url)
        common.enumerate_validate(self.app.pargs.enumerate, self.valid_enumerate)

        if enumerate == "p":
            finds = self.enumerate_plugins(url)
            noun = "plugins"
        elif enumerate == "u":
            self.enumerate_users(url)
        elif enumerate == "t":
            self.enumerate_themes(url)

        print common.template("common/list_noun.tpl", {"noun":noun,
            "items":finds, "empty":len(finds) == 0, "Noun":noun.capitalize()})

    def enumerate_users(self, url):
        raise NotImplementedError("Not implemented yet.")

    def enumerate_plugins(self, url):
        raise NotImplementedError("Not implemented yet.")

    def enumerate_themes(self, url):
        raise NotImplementedError("Not implemented yet.")
