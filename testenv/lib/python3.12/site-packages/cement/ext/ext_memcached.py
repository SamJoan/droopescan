"""
Cement memcached extension module.

**Note** This extension has an external dependency on ``pylibmc``. Cement
explicitly does **not** include external dependencies for optional
extensions.

* In Cement ``>=3.0.8`` you must include ``cement[memcached]`` in your
  applications dependencies.
* In Cement ``<3.0.8`` you must include ``pylibmc`` in your applications
  dependencies.
"""

from __future__ import annotations
import pylibmc  # type: ignore
from typing import Any, List, Optional, TYPE_CHECKING
from ..core import cache
from ..utils.misc import minimal_logger

if TYPE_CHECKING:
    from ..core.foundation import App  # pragma: nocover

LOG = minimal_logger(__name__)


class MemcachedCacheHandler(cache.CacheHandler):

    """
    This class implements the :ref:`Cache <cement.core.cache>` Handler
    interface.  It provides a caching interface using the
    `pylibmc <http://sendapatch.se/projects/pylibmc/>`_ library.
    """

    class Meta(cache.CacheHandler.Meta):

        """Handler meta-data."""

        label = 'memcached'
        config_defaults = dict(
            hosts=['127.0.0.1'],
            expire_time=0,
        )

    _meta: Meta  # type: ignore

    def __init__(self, *args: Any, **kw: Any) -> None:
        super(MemcachedCacheHandler, self).__init__(*args, **kw)
        self.mc = None

    def _setup(self, *args: Any, **kw: Any) -> None:
        super(MemcachedCacheHandler, self)._setup(*args, **kw)
        self._fix_hosts()
        self.mc = pylibmc.Client(self._config('hosts'))

    def _fix_hosts(self) -> None:
        """
        Useful to fix up the hosts configuration (i.e. convert a
        comma-separated string into a list).  This function does not return
        anything, however it is expected to set the `hosts` value of the
        ``[cache.memcached]`` section (which is what this extension reads for
        its host configution).

        :returns: ``None``

        """
        hosts: List[str] = self._config('hosts')
        fixed_hosts = []

        if type(hosts) is str:
            parts = hosts.split(',')
            for part in parts:
                fixed_hosts.append(part.strip())
        elif type(hosts) is list:
            fixed_hosts = hosts
        self.app.config.set(self._meta.config_section, 'hosts', fixed_hosts)

    def get(self, key: str, fallback: Any = None, **kw: Any) -> Any:
        """
        Get a value from the cache.  Any additional keyword arguments will be
        passed directly to `pylibmc` get function.

        Args:
            key (str): The key of the item in the cache to get.

        Keyword Args:
            fallback: The value to return if the item is not found in the
                cache.

        Returns:
            unknown: The value of the item in the cache, or the ``fallback``
            value.

        """
        LOG.debug(f"getting cache value using key '{key}'")
        res = self.mc.get(key, **kw)
        if res is None:
            return fallback
        else:
            return res

    def _config(self, key: str) -> Any:
        """
        This is a simple wrapper, and is equivalent to:
        ``self.app.config.get('cache.memcached', <key>)``.

        Args:
            key (str): The key to get a config value from the 'cache.memcached'
                config section.

        Returns:
            unknown: The value of the given key.

        """
        return self.app.config.get(self._meta.config_section, key)

    def set(self, key: str, value: Any, time: Optional[int] = None, **kw: Any) -> None:
        """
        Set a value in the cache for the given ``key``.  Any additional
        keyword arguments will be passed directly to the `pylibmc` set
        function.

        Args:
            key (str): The key of the item in the cache to set.
            value: The value of the item to set.

        Keyword Arguments:
            time (int): The expiration time (in seconds) to keep the item
                cached.  Defaults to `expire_time` as defined in the
                applications configuration.

        """
        if time is None:
            time = int(self._config('expire_time'))

        self.mc.set(key, value, time=time, **kw)

    def delete(self, key: str, **kw: Any) -> bool:
        """
        Delete an item from the cache for the given ``key``.  Any additional
        keyword arguments will be passed directly to the `pylibmc` delete
        function.

        Args:
            key (str): The key to delete from the cache.

        """
        self.mc.delete(key, **kw)
        return True

    def purge(self, **kw: Any) -> None:
        """
        Purge the entire cache, all keys and values will be lost.  Any
        additional keyword arguments will be passed directly to the
        pylibmc ``flush_all()`` function.

        """

        self.mc.flush_all(**kw)


def load(app: App) -> None:
    app.handler.register(MemcachedCacheHandler)
