from cement.core import handler, controller

class DrupalScanner(controller.CementBaseController):
    class Meta:
        label = 'drupalscanner'
        stacked_on = 'base'

    @controller.expose(help='drupal-related scanning tools')
    def drupal(self):
        url = self.app.pargs.url
        if not url:
            raise RuntimeError("--url was not specified.")

def load():
    handler.register(DrupalScanner)

