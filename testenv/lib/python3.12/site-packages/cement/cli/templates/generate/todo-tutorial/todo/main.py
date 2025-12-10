
import os
from tinydb import TinyDB
from cement import App, TestApp, init_defaults
from cement.core.exc import CaughtSignal
from cement.utils import fs
from .core.exc import TodoError
from .controllers.base import Base
from .controllers.items import Items


# configuration defaults
CONFIG = init_defaults('todo')
CONFIG['todo']['foo'] = 'bar'
CONFIG['todo']['db_file'] = '~/.todo/db.json'
CONFIG['todo']['email'] = 'you@yourdomain.com'


def extend_tinydb(app):
    app.log.info('extending todo application with tinydb')
    db_file = app.config.get('todo', 'db_file')

    # ensure that we expand the full path
    db_file = fs.abspath(db_file)
    app.log.info(f'tinydb database file is: {db_file}')

    # ensure our parent directory exists
    db_dir = os.path.dirname(db_file)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    app.extend('db', TinyDB(db_file))


class Todo(App):
    """My TODO Application primary application."""

    class Meta:
        label = 'todo'

        # configuration defaults
        config_defaults = CONFIG

        # call sys.exit() on close
        close_on_exit = True

        # load additional framework extensions
        extensions = [
            'yaml',
            'colorlog',
            'jinja2',
        ]

        # configuration handler
        config_handler = 'yaml'

        # configuration file suffix
        config_file_suffix = '.yml'

        # set the log handler
        log_handler = 'colorlog'

        # set the output handler
        output_handler = 'jinja2'

        # register handlers
        handlers = [
            Base,
            Items,
        ]

        # register hooks
        hooks = [
            ('post_setup', extend_tinydb),
        ]


class TodoTest(TestApp,Todo):
    """A sub-class of Todo that is better suited for testing."""

    class Meta:
        label = 'todo'


def main():
    with Todo() as app:
        try:
            app.run()

        except AssertionError as e:
            print(f'AssertionError > {e.args[0]}')
            app.exit_code = 1

            if app.debug is True:
                import traceback
                traceback.print_exc()

        except TodoError:
            print(f'TodoError > {e.args[0]}')
            app.exit_code = 1

            if app.debug is True:
                import traceback
                traceback.print_exc()

        except CaughtSignal as e:
            # Default Cement signals are SIGINT and SIGTERM, exit 0 (non-error)
            print(f'\n{e}')
            app.exit_code = 0


if __name__ == '__main__':
    main()
