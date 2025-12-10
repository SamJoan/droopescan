
from cement import App, CaughtSignal, Controller, ex, get_version

VERSION = (0, 0, 1, 'alpha', 0)

VERSION_BANNER = """
{{ label }} v%s
""" % get_version(VERSION)


class Base(Controller):
    class Meta:
        label = 'base'

        arguments = [
            ### add a version banner
            ( [ '-v', '--version' ],
              { 'action'  : 'version',
                'version' : VERSION_BANNER } ),
        ]


    def _default(self):
        """Default action if no sub-command is passed."""

        self.app.args.print_help()


    @ex(
        help='example sub command1',
        arguments=[
            ### add a sample foo option under subcommand namespace
            ( [ '-f', '--foo' ],
              { 'help' : 'notorious foo option',
                'action'  : 'store',
                'dest' : 'foo' } ),
        ],
    )
    def command1(self):
        """Example sub-command."""

        print('Inside Base.command1')

        ### do something with arguments
        if self.app.pargs.foo is not None:
            print(f'Foo Argument > {self.app.pargs.foo}')


class MyApp(App):

    class Meta:
        # application label
        label = '{{ label }}'

        # register handlers
        handlers = [
            Base
        ]

        # call sys.exit() on close
        close_on_exit = True


def main():
    with MyApp() as app:
        try:
            app.run()
        except CaughtSignal as e:
            # Default Cement signals are SIGINT and SIGTERM, exit 0 (non-error)
            print(f'\n{e}')
            app.exit_code = 0


if __name__ == '__main__':
    main()
