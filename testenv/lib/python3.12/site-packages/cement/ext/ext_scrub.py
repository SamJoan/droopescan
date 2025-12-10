"""
Cement scrub extension module.
"""

from __future__ import annotations
import re
from typing import TYPE_CHECKING
from .. import Controller
from ..utils.misc import minimal_logger

if TYPE_CHECKING:
    from ..core.foundation import App  # pragma: nocover

LOG = minimal_logger(__name__)


def scrub_output(app: App, text: str) -> str:
    if app.pargs.scrub:
        text = app.scrub(text)
    return text


def extend_scrub(app: App) -> None:
    def scrub(text: str) -> str:
        if not hasattr(app._meta, 'scrub') or app._meta.scrub is None:
            return text  # pragma: nocover
        elif isinstance(text, str):
            for regex, replace in app._meta.scrub:
                text = re.sub(regex, replace, text)
        else:
            LOG.debug(f'text is not str > {type(text)}')
        return text

    app.extend('scrub', scrub)


class ScrubController(Controller):
    """
    Add embedded options to the base controller to support scrubbing output.
    """

    class Meta(Controller.Meta):
        #: Controller label
        label = 'scrub'

        #: Parent controller to stack ontop of
        stacked_on = 'base'

        #: Stacking method
        stacked_type = 'embedded'

        #: Command line argument options
        argument_options = ['--scrub']

        #: Command line argument options help
        argument_help = 'obfuscate sensitive data from rendered output'

    _meta: Meta  # type: ignore

    def _pre_argument_parsing(self) -> None:
        if self._meta.argument_options is not None:
            assert isinstance(self._meta.argument_options, list), \
                "ScrubController.Meta.argument_options must be a list"
            self.app.args.add_argument(*self._meta.argument_options,
                                       help=self._meta.argument_help,
                                       action='store_true',
                                       dest='scrub')


def load(app: App) -> None:
    app.handler.register(ScrubController)
    app.hook.register('post_render', scrub_output)
    app.hook.register('pre_argument_parsing', extend_scrub)
