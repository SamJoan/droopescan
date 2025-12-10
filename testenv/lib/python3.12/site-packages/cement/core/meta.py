"""Cement core meta functionality."""

from typing import Any, Dict


class Meta(object):

    """
    Container class for meta attributes of a larger class. Keyword arguments
    are set as attributes of ``self``.

    """

    def __init__(self, **kwargs: Any) -> None:
        self._merge(kwargs)

    def _merge(self, dict_obj: Dict[str, Any]) -> None:
        for key in dict_obj.keys():
            setattr(self, key, dict_obj[key])


class MetaMixin(object):

    """
    Mixin that provides the meta class support to add settings to instances
    of objects. Meta keys cannot start with a ``_``.

    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Get a List of all the Classes we in our MRO, find any attribute named
        #     Meta on them, and then merge them together in order of MRO
        metas = reversed([x.Meta for x in self.__class__.mro()
                          if hasattr(x, "Meta")])
        final_meta = {}

        # Merge the Meta classes into one dict
        for meta in metas:
            final_meta.update(dict([x for x in meta.__dict__.items()
                                    if not x[0].startswith("_")]))

        # Update the final Meta with any kwargs passed in
        for key in final_meta.keys():
            if key in kwargs:
                final_meta[key] = kwargs.pop(key)

        self._meta = Meta(**final_meta)

        # FIX ME: object.__init__() doesn't take params without exception
        super(MetaMixin, self).__init__()
