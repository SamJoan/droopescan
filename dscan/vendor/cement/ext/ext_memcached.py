"""Memcached Framework Extension."""

import sys
import pylibmc
from ..core import cache, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class MemcachedCacheHandler(cache.CementCacheHandler):

    """
    This class implements the :ref:`ICache <cement.core.cache>`
    interface.  It provides a caching interface using the
    `pylibmc <http://sendapatch.se/projects/pylibmc/>`_ library.

    **Note** This extension has an external dependency on `pylibmc`.  You
    must include `pylibmc` in your applications dependencies as Cement
    explicitly does *not* include external dependencies for optional
    extensions.

    **Note** This extension is not supported on Python 3, due to the fact
    that `pylibmc` does not appear to support Python 3 as of yet.

    Configuration:

    The Memcached extension is configurable with the following config settings
    under a `[cache.memcached]` section of the application configuration.

        * **expire_time** - The default time in second to expire items in the
          cache.  Default: 0 (does not expire).
        * **hosts** - List of Memcached servers.

    Configurations can be passed as defaults to a CementApp:

    .. code-block:: python

        from cement.core import foundation, backend
        from cement.utils.misc import init_defaults

        defaults = init_defaults('myapp', 'cache.memcached')
        defaults['cache.memcached']['expire_time'] = 0
        defaults['cache.memcached']['hosts'] = ['127.0.0.1']

        app = foundation.CementApp('myapp',
                                   config_defaults=defaults,
                                   cache_handler='memcached',
                                   )


    Additionally, an application configuration file might have a section like
    the following:

    .. code-block:: text

        [myapp]

        # set the cache handler to use
        cache_handler = memcached


        [cache.memcached]

        # time in seconds that an item in the cache will expire
        expire_time = 3600

        # comma seperated list of memcached servers
        hosts = 127.0.0.1, cache.example.com


    Usage:

    .. code-block:: python

        from cement.core import foundation
        from cement.utils.misc import init_defaults

        defaults = init_defaults('myapp', 'memcached')
        defaults['cache.memcached']['expire_time'] = 300 # seconds
        defaults['cache.memcached']['hosts'] = ['127.0.0.1']

        class MyApp(foundation.CementApp):
            class Meta:
                label = 'myapp'
                config_defaults = defaults
                extensions = ['memcached']
                cache_handler = 'memcached'

        with MyApp() as app:
            # Run the app
            app.run()

            # Set a cached value
            app.cache.set('my_key', 'my value')

            # Get a cached value
            app.cache.get('my_key')

            # Delete a cached value
            app.cache.delete('my_key')

            # Delete the entire cache
            app.cache.purge()

    """
    class Meta:
        interface = cache.ICache
        label = 'memcached'
        config_defaults = dict(
            hosts=['127.0.0.1'],
            expire_time=0,
        )

    def __init__(self, *args, **kw):
        super(MemcachedCacheHandler, self).__init__(*args, **kw)
        self.mc = None

    def _setup(self, *args, **kw):
        super(MemcachedCacheHandler, self)._setup(*args, **kw)
        self._fix_hosts()
        self.mc = pylibmc.Client(self._config('hosts'))

    def _fix_hosts(self):
        """
        Useful to fix up the hosts configuration (i.e. convert a
        comma-separated string into a list).  This function does not return
        anything, however it is expected to set the `hosts` value of the
        `[cache.memcached]` section (which is what this extension reads for
        it's host configution).

        :returns: None

        """
        hosts = self._config('hosts')
        fixed_hosts = []

        if type(hosts) == str:
            parts = hosts.split(',')
            for part in parts:
                fixed_hosts.append(part.strip())
        elif type(hosts) == list:
            fixed_hosts = hosts
        self.app.config.set(self._meta.config_section, 'hosts', fixed_hosts)

    def get(self, key, fallback=None, **kw):
        """
        Get a value from the cache.  Any additional keyword arguments will be
        passed directly to `pylibmc` get function.

        :param key: The key of the item in the cache to get.
        :param fallback: The value to return if the item is not found in the
         cache.
        :returns: The value of the item in the cache, or the `fallback` value.

        """
        LOG.debug("getting cache value using key '%s'" % key)
        res = self.mc.get(key, **kw)
        if res is None:
            return fallback
        else:
            return res

    def _config(self, key):
        """
        This is a simple wrapper, and is equivalent to:
        `self.app.config.get('cache.memcached', <key>)`.

        :param key: The key to get a config value from the 'cache.memcached'
         config section.
        :returns: The value of the given key.

        """
        return self.app.config.get(self._meta.config_section, key)

    def set(self, key, value, time=None, **kw):
        """
        Set a value in the cache for the given `key`.  Any additional
        keyword arguments will be passed directly to the `pylibmc` set
        function.

        :param key: The key of the item in the cache to set.
        :param value: The value of the item to set.
        :param time: The expiration time (in seconds) to keep the item cached.
         Defaults to `expire_time` as defined in the applications
         configuration.
        :returns: None

        """
        if time is None:
            time = int(self._config('expire_time'))

        self.mc.set(key, value, time=time, **kw)

    def delete(self, key, **kw):
        """
        Delete an item from the cache for the given `key`.  Any additional
        keyword arguments will be passed directly to the `pylibmc` delete
        function.

        :param key: The key to delete from the cache.
        :returns: None

        """
        self.mc.delete(key, **kw)

    def purge(self, **kw):
        """
        Purge the entire cache, all keys and values will be lost.  Any
        additional keyword arguments will be passed directly to the
        `pylibmc` flush_all() function.

        :returns: None

        """

        self.mc.flush_all(**kw)


def load(app):
    handler.register(MemcachedCacheHandler)
