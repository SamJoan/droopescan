"""Misc utilities."""

import os
import sys
import logging
import hashlib
from textwrap import TextWrapper
from random import random


def rando(salt=None):
    """
    Generate a random MD5 hash for whatever purpose.  Useful for testing
    or any other time that something random is required.

    :param salt: Optional 'salt', if None then random() is used.
    :returns: Random MD5 hash (str).
    """

    if salt is None:
        salt = random()

    return hashlib.md5(str(salt).encode()).hexdigest()


# class NullLogger(object):
#    def __init__(self, namespace, debug, *args, **kw):
#        pass

    # def info(self, *args, **kw):
    #     pass

    # def warn(self, *args, **kw):
    #     pass

    # def error(self, *args, **kw):
    #     pass

    # def fatal(self, *args, **kw):
    #     pass

    # def debug(self, *args, **kw):
    #     pass

class MinimalLogger(object):

    def __init__(self, namespace, debug, *args, **kw):
        self.namespace = namespace
        self.backend = logging.getLogger(namespace)
        formatter = logging.Formatter(
            "%(asctime)s (%(levelname)s) %(namespace)s : %(message)s"
        )
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.setLevel(logging.INFO)
        self.backend.setLevel(logging.INFO)

        # FIX ME: really don't want to hard check sys.argv like this but
        # can't figure any better way get logging started (only for debug)
        # before the app logging is setup.
        if '--debug' in sys.argv or debug:
            console.setLevel(logging.DEBUG)
            self.backend.setLevel(logging.DEBUG)

        self.backend.addHandler(console)

    def _get_logging_kwargs(self, namespace, **kw):
        if not namespace:
            namespace = self.namespace

        if 'extra' in kw.keys() and 'namespace' in kw['extra'].keys():
            pass
        elif 'extra' in kw.keys() and 'namespace' not in kw['extra'].keys():
            kw['extra']['namespace'] = namespace
        else:
            kw['extra'] = dict(namespace=namespace)

        return kw

    @property
    def logging_is_enabled(self):
        if 'CEMENT_FRAMEWORK_LOGGING' in os.environ.keys():
            if is_true(os.environ['CEMENT_FRAMEWORK_LOGGING']):
                res = True
            else:
                res = False
        else:
            res = True

        return res

    def info(self, msg, namespace=None, **kw):
        if self.logging_is_enabled:
            kwargs = self._get_logging_kwargs(namespace, **kw)
            self.backend.info(msg, **kwargs)

    def warn(self, msg, namespace=None, **kw):
        if self.logging_is_enabled:
            kwargs = self._get_logging_kwargs(namespace, **kw)
            self.backend.warn(msg, **kwargs)

    def error(self, msg, namespace=None, **kw):
        if self.logging_is_enabled:
            kwargs = self._get_logging_kwargs(namespace, **kw)
            self.backend.error(msg, **kwargs)

    def fatal(self, msg, namespace=None, **kw):
        if self.logging_is_enabled:
            kwargs = self._get_logging_kwargs(namespace, **kw)
            self.backend.fatal(msg, **kwargs)

    def debug(self, msg, namespace=None, **kw):
        if self.logging_is_enabled:
            kwargs = self._get_logging_kwargs(namespace, **kw)
            self.backend.debug(msg, **kwargs)


def init_defaults(*sections):
    """
    Returns a standard dictionary object to use for application defaults.
    If sections are given, it will create a nested dict for each section name.

    :arg sections: Section keys to create nested dictionaries for.
    :returns: Dictionary of nested dictionaries (sections)
    :rtype: dict

    .. code-block:: python

        from cement.core import foundation
        from cement.utils.misc import init_defaults

        defaults = init_defaults('myapp', 'section2', 'section3')
        defaults['myapp']['debug'] = False
        defaults['section2']['foo'] = 'bar
        defaults['section3']['foo2'] = 'bar2'

        app = foundation.CementApp('myapp', config_defaults=defaults)

    """
    defaults = dict()
    for section in sections:
        defaults[section] = dict()
    return defaults


def minimal_logger(namespace, debug=False):
    """
    Setup just enough for cement to be able to do debug logging.  This is the
    logger used by the Cement framework, which is setup and accessed before
    the application is functional (and more importantly before the
    applications log handler is usable).

    :param namespace: The logging namespace.  This is generally '__name__' or
        anything you want.
    :param debug: Toggle debug output. Default: False
    :type debug: boolean
    :returns: Logger object

    .. code-block:: python

        from cement.utils.misc import minimal_logger
        LOG = minimal_logger('cement')
        LOG.debug('This is a debug message')

    """
    return MinimalLogger(namespace, debug)


def is_true(item):
    """
    Given a value, determine if it is one of [True, 'True', 'true', 1, '1'].

    :param item: The item to convert to a boolean.
    :returns: True if `item` is in ``[True, 'True', 'true', 1, '1']``, False
        otherwise.
    :rtype: boolean

    """
    if item in [True, 'True', 'true', 1, '1']:
        return True
    else:
        return False


def wrap(text, width=77, indent='', long_words=False, hyphens=False):
    """
    Wrap text for cleaner output (this is a simple wrapper around
    `textwrap.TextWrapper` in the standard library).

    :param text: The text to wrap
    :param width: The max width of a line before breaking
    :param indent: String to prefix subsequent lines after breaking
    :param long_words: Break on long words
    :param hyphens: Break on hyphens
    :returns: str(text)

    """
    if type(text) != str:
        raise TypeError("`text` must be a string.")

    wrapper = TextWrapper(subsequent_indent=indent, width=width,
                          break_long_words=long_words,
                          break_on_hyphens=hyphens)
    return wrapper.fill(text)
