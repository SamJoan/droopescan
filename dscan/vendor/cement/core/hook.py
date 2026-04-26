"""Cement core hooks module."""

import operator
from ..core import backend, exc
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


def define(name):
    """
    Define a hook namespace that plugins can register hooks in.

    :param name: The name of the hook, stored as hooks['name']
    :raises: cement.core.exc.FrameworkError

    Usage:

    .. code-block:: python

        from cement.core import hook

        hook.define('myhookname_hook')

    """
    LOG.debug("defining hook '%s'" % name)
    if name in backend.__hooks__:
        raise exc.FrameworkError("Hook name '%s' already defined!" % name)
    backend.__hooks__[name] = []


def defined(hook_name):
    """
    Test whether a hook name is defined.

    :param hook_name: The name of the hook.
        I.e. ``my_hook_does_awesome_things``.
    :returns: True if the hook is defined, False otherwise.
    :rtype: boolean

    """
    if hook_name in backend.__hooks__:
        return True
    else:
        return False


def register(name, func, weight=0):
    """
    Register a function to a hook.  The function will be called, in order of
    weight, when the hook is run.

    :param name: The name of the hook to register too.  I.e. ``pre_setup``,
        ``post_run``, etc.
    :param func:    The function to register to the hook.  This is an
        *un-instantiated*, non-instance method, simple function.
    :param weight:  The weight in which to order the hook function.
    :type weight: integer

    Usage:

    .. code-block:: python

        from cement.core import hook

        def my_hook(*args, **kwargs):
            # do something here
            res = 'Something to return'
            return res

        hook.register('post_setup', my_hook)

    """
    if name not in backend.__hooks__:
        LOG.debug("hook name '%s' is not defined! ignoring..." % name)
        return False

    LOG.debug("registering hook '%s' from %s into hooks['%s']" %
              (func.__name__, func.__module__, name))

    # Hooks are as follows: (weight, name, func)
    backend.__hooks__[name].append((int(weight), func.__name__, func))


def run(name, *args, **kwargs):
    """
    Run all defined hooks in the namespace.  Yields the result of each hook
    function run.

    :param name: The name of the hook function.
    :param args: Additional arguments to be passed to the hook functions.
    :param kwargs: Additional keyword arguments to be passed to the hook
        functions.
    :raises: FrameworkError

    Usage:

    .. code-block:: python

        from cement.core import hook

        for result in hook.run('hook_name'):
            # do something with result from each hook function
            ...
    """
    if name not in backend.__hooks__:
        raise exc.FrameworkError("Hook name '%s' is not defined!" % name)

    # Will order based on weight (the first item in the tuple)
    backend.__hooks__[name].sort(key=operator.itemgetter(0))
    for hook in backend.__hooks__[name]:
        LOG.debug("running hook '%s' (%s) from %s" %
                  (name, hook[2], hook[2].__module__))
        res = hook[2](*args, **kwargs)

        # Results are yielded, so you must fun a for loop on it, you can not
        # simply call run_hooks().
        yield res
