from cement.core import handler, controller
import common

class BasePlugin(controller.CementBaseController):

    valid_enumerate = ['u', 'p', 't']

    class Meta:
        label = 'baseplugin'
        stacked_on = 'base'

        arguments = [
                (['--enumerate', '-e'], dict(action='store',
                help="""What to enumerate. Available options are u, p and t. These
                    ennumerate users, plugins and themes respectively.""")),
            ]

    def enumerate_route(self):
        url, enumerate = self.app.pargs.url, self.app.pargs.enumerate

        common.url_validate(self.app.pargs.url)
        common.enumerate_validate(self.app.pargs.enumerate, self.valid_enumerate)

        if enumerate == "p":
            plugins = self.enumerate_plugins(url)
            print plugins
        elif enumerate == "u":
            self.enumerate_users(url)
        elif enumerate == "t":
            self.enumerate_themes(url)

    def enumerate_users(self, url):
        raise NotImplementedError("Not implemented yet.")

    def enumerate_plugins(self, url):
        raise NotImplementedError("Not implemented yet.")

    def enumerate_themes(self, url):
        raise NotImplementedError("Not implemented yet.")
