from cement.core import handler, controller
from plugins import HumanBasePlugin

class Update(HumanBasePlugin):
    class Meta:
        label = 'update'
        stacked_on = 'base'
        stacked_type = 'nested'
        hide = True

        arguments = [
                (['--cms', '-c'], dict(action='store', required=True,
                    help='Which CMS to generate the XML for', choices=['drupal',
                        'ss'])),
                (['--selection', '-s'], dict(action='store',
                    help='Comma separated list of versions for drupal_select.'))
            ]

    @controller.expose(help='', hide=True)
    def update(self):
        pass

def load():
    handler.register(Update)
