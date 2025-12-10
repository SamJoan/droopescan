
from __future__ import annotations
from typing import Optional, List
from cement import App, CaughtSignal  # noqa: E402
from .controllers.base import Base    # noqa: E402
from cement.core.exc import FrameworkError


class CementApp(App):
    class Meta:
        label = 'cement'
        controller = 'base'
        template_module = 'cement.cli.templates'
        template_handler = 'jinja2'
        config_handler = 'yaml'
        config_file_suffix = '.yml'

        extensions = [
            'generate',
            'yaml',
            'jinja2',
        ]

        handlers = [
            Base,
        ]


class CementTestApp(CementApp):
    class Meta:
        argv: List[str] = []
        config_files: List[str] = []
        exit_on_close = False


def main(argv: Optional[List[str]] = None) -> None:
    # Issue #679: https://github.com/datafolklabs/cement/issues/679
    try:
        import yaml, jinja2  # type: ignore  # noqa: F401 E401
    except ModuleNotFoundError:  # pragma: nocover
        raise FrameworkError('Cement CLI Dependencies are missing! Install cement[cli] extras ' +
                             'package to resolve -> pip install cement[cli]')

    with CementApp() as app:
        try:
            app.run()
        except AssertionError as e:                     # pragma: nocover
            print(f'AssertionError > {e.args[0]}')      # pragma: nocover
            app.exit_code = 1                           # pragma: nocover
        except CaughtSignal as e:                       # pragma: nocover
            print(f'\n{e}')                             # pragma: nocover
            app.exit_code = 0                           # pragma: nocover


if __name__ == '__main__':
    main()                                              # pragma: nocover
