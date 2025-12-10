"""
Cement redis extension module.

**Note** This extension has an external dependency on ``redis``. Cement
explicitly does **not** include external dependencies for optional
extensions.

* In Cement ``>=3.0.8`` you must include ``cement[redis]`` in your
  applications dependencies.
* In Cement ``<3.0.8`` you must include ``redis`` in your applications
  dependencies.
"""

from __future__ import annotations
import redis
from typing import Any, Optional, TYPE_CHECKING
from ..core import cache
from ..utils.misc import minimal_logger

if TYPE_CHECKING:
    from ..core.foundation import App  # pragma: nocover

LOG = minimal_logger(__name__)


class RedisCacheHandler(cache.CacheHandler):

    """
    This class implements the :ref:`Cache <cement.core.cache>` Handler
    interface.  It provides a caching interface using the
    `redis <http://github.com/andymccurdy/redis-py>`_ library.
    """

    class Meta(cache.CacheHandler.Meta):

        """Handler meta-data."""

        label = 'redis'
        config_defaults = dict(
            host='127.0.0.1',
            port=6379,
            db=0,
            expire_time=0,
        )

    _meta: Meta  # type: ignore

    def __init__(self, *args: Any, **kw: Any) -> None:
        super(RedisCacheHandler, self).__init__(*args, **kw)
        self.mc = None

    def _setup(self, *args: Any, **kw: Any) -> None:
        super(RedisCacheHandler, self)._setup(*args, **kw)
        self.r = redis.StrictRedis(
            host=self._config('host', default='127.0.0.1'),
            port=self._config('port', default=6379),
            db=self._config('db', default=0))

    def _config(self, key: str, default: Any = None) -> Any:
        """
        This is a simple wrapper, and is equivalent to:
        ``self.app.config.get('cache.redis', <key>)``.

        Args:
            key (str): The key to get a config value from the ``cache.redis``
                config section.

        Returns:
            unknown: The value of the given key.

        """
        return self.app.config.get(self._meta.config_section, key)

    def get(self, key: str, fallback: Any = None, **kw: Any) -> Any:
        """
        Get a value from the cache.  Additional keyword arguments are ignored.

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
        res = self.r.get(key)
        if res is None:
            return fallback
        else:
            return res.decode('utf-8')

    def set(self, key: str, value: Any, time: Optional[int] = None, **kw: Any) -> None:
        """
        Set a value in the cache for the given ``key``.  Additional
        keyword arguments are ignored.

        Args:
            key (str): The key of the item in the cache to set.
            value: The value of the item to set.
            time (int): The expiration time (in seconds) to keep the item
                cached. Defaults to ``expire_time`` as defined in the
                applications configuration.

        """
        if time is None:
            time = int(self._config('expire_time'))

        if time == 0:
            self.r.set(key, value)
        else:
            self.r.setex(key, time, value)

    def delete(self, key: str, **kw: Any) -> bool:
        """
        Delete an item from the cache for the given ``key``.  Additional
        keyword arguments are ignored.

        Args:
            key (str): The key to delete from the cache.

        Returns:
            bool: ``True`` if the key is successfully deleted, ``False``
            otherwise
        """
        res = self.r.delete(key)
        return int(res) > 0

    def purge(self, **kw: Any) -> None:
        """
        Purge the entire cache, all keys and values will be lost.  Any
        additional keyword arguments will be passed directly to the
        redis ``flush_all()`` function.

        """
        keys = self.r.keys('*')
        if keys:
            self.r.delete(*keys)


def load(app: App) -> None:
    app.handler.register(RedisCacheHandler)
