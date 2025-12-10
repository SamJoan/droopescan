"""
Cement alarm extension module.
"""

from __future__ import annotations
import signal
from typing import Any, TYPE_CHECKING
from ..utils.misc import minimal_logger

if TYPE_CHECKING:
    from ..core.foundation import App  # pragma: nocover

LOG = minimal_logger(__name__)


def alarm_handler(app: App, signum: int, frame: Any) -> None:
    if signum == signal.SIGALRM:
        app.log.error(app.alarm.msg)


class AlarmManager(object):
    """
    Lets the developer easily set and stop an alarm.  If the
    alarm exceeds the given time it will raise ``signal.SIGALRM``.

    """

    def __init__(self, *args: Any, **kw: Any) -> None:
        super(AlarmManager, self).__init__(*args, **kw)
        self.msg: str = None  # type: ignore

    def set(self, time: int, msg: str) -> None:
        """
        Set the application alarm to ``time`` seconds.  If the time is
        exceeded ``signal.SIGALRM`` is raised.

        Args:
            time (int): The time in seconds to set the alarm to.
            msg (str): The message to display if the alarm is triggered.
        """

        LOG.debug(f'setting application alarm for {time} seconds')
        self.msg = msg
        signal.alarm(int(time))

    def stop(self) -> None:
        """
        Stop the application alarm.
        """
        LOG.debug('stopping application alarm')
        signal.alarm(0)


def load(app: App) -> None:
    app.catch_signal(signal.SIGALRM)
    app.extend('alarm', AlarmManager())
    app.hook.register('signal', alarm_handler)
