"""Cement core exceptions module."""


class FrameworkError(Exception):

    """
    General framework (non-application) related errors.

    :param msg: The error message.

    """

    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg

    def __str__(self):
        return self.msg


class InterfaceError(FrameworkError):

    """Interface related errors."""
    pass


class CaughtSignal(FrameworkError):

    """
    Raised when a defined signal is caught.  For more information regarding
    signals, reference the
    `signal <http://docs.python.org/library/signal.html>`_ library.

    :param signum: The signal number.
    :param frame: The signal frame.

    """

    def __init__(self, signum, frame):
        msg = 'Caught signal %s' % signum
        super(CaughtSignal, self).__init__(msg)
        self.signum = signum
        self.frame = frame
