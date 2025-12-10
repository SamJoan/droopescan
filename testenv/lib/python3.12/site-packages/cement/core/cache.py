"""Cement core cache module."""

from abc import abstractmethod
from typing import Any, Optional
from ..core.interface import Interface
from ..core.handler import Handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class CacheInterface(Interface):

    """
    This class defines the Cache Interface.  Handlers that implement this
    interface must provide the methods and attributes defined below. In
    general, most implementations should sub-class from the provided
    :class:`CacheHandler` base class as a starting point.
    """

    class Meta(Interface.Meta):

        """Handler meta-data."""

        #: The string identifier of the interface.
        interface = 'cache'

    @abstractmethod
    def get(self, key: str, fallback: Any = None) -> Any:
        """
        Get the value for a key in the cache.

        If the key does not exist or the key/value in cache is expired, this
        functions must return ``fallback`` (which in turn must default to
        ``None``).

        Args:
            key (str): The key of the value stored in cache

        Keyword Args:
            fallback: Optional value that is returned if the cache is
                expired or the key does not exist.

        Returns:
            Unknown: Whatever the value is in the cache, or the ``fallback``

        """
        pass    # pragma: nocover

    @abstractmethod
    def set(self, key: str, value: Any, time: Optional[int] = None) -> None:
        """
        Set the key/value in the cache for a set amount of ``time``.

        Args:
            key (str): The key of the value to store in cache
            value (unknown): The value of that key to store in cache

        Keyword Args:
            time (int): A one-off expire time in seconds (or ``None``.  If no
                time is given, then a default value is used (determined by the
                implementation).

        Returns: None

        """
        pass    # pragma: nocover

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Deletes a key/value from the cache.

        Args:
            key: The key in the cache to delete

        Returns:
            bool: ``True`` if the key is successfully deleted, ``False``
            otherwise

        """
        pass    # pragma: nocover

    @abstractmethod
    def purge(self) -> None:
        """
        Clears all data from the cache.

        """
        pass    # pragma: nocover


class CacheHandler(CacheInterface, Handler):

    """
    Cache handler implementation.

    """
    class Meta(Handler.Meta):
        pass    # pragma: nocover
