"""Cement core cache module."""

from ..core import interface, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


def cache_validator(klass, obj):
    """Validates a handler implementation against the ICache interface."""

    members = [
        '_setup',
        'get',
        'set',
        'delete',
        'purge',
    ]
    interface.validate(ICache, obj, members)


class ICache(interface.Interface):

    """
    This class defines the Cache Handler Interface.  Classes that
    implement this handler must provide the methods and attributes defined
    below.

    Implementations do *not* subclass from interfaces.

    Usage:

    .. code-block:: python

        from cement.core import cache

        class MyCacheHandler(object):
            class Meta:
                interface = cache.ICache
                label = 'my_cache_handler'
            ...

    """
    # pylint: disable=W0232, C0111, R0903
    class IMeta:

        """Interface meta-data."""

        label = 'cache'
        """The label (or type identifier) of the interface."""

        validator = cache_validator
        """Interface validator function."""

    # Must be provided by the implementation
    Meta = interface.Attribute('Handler meta-data')

    def _setup(app_obj):
        """
        The _setup function is called during application initialization and
        must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object.
        :returns: None

        """

    def get(key, fallback=None):
        """
        Get the value for a key in the cache.  If the key does not exist
        or the key/value in cache is expired, this functions must return
        'fallback' (which in turn must default to None).

        :param key: The key of the value stored in cache
        :param fallback: Optional value that is returned if the cache is
         expired or the key does not exist.  Default: None
        :returns: Unknown (whatever the value is in cache, or the `fallback`)

        """

    def set(key, value, time=None):
        """
        Set the key/value in the cache for a set amount of `time`.

        :param key: The key of the value to store in cache.
        :param value: The value of that key to store in cache.
        :param time: A one-off expire time.  If no time is given, then a
            default value is used (determined by the implementation).
        :type time: integer (seconds) or None
        :returns: None

        """

    def delete(key):
        """
        Deletes a key/value from the cache.

        :param key: The key in the cache to delete.
        :returns: True if the key is successfully deleted, False otherwise.
        :rtype: boolean

        """

    # pylint: disable=E0211
    def purge():
        """
        Clears all data from the cache.

        """


class CementCacheHandler(handler.CementBaseHandler):

    """
    Base class that all Cache Handlers should sub-class from.

    """
    class Meta:

        """
        Handler meta-data (can be passed as keyword arguments to the parent
        class).
        """

        label = None
        """String identifier of this handler implementation."""

        interface = ICache
        """The interface that this handler class implements."""

    def __init__(self, *args, **kw):
        super(CementCacheHandler, self).__init__(*args, **kw)
