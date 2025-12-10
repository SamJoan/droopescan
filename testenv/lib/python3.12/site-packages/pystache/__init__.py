"""
TODO: add a docstring.

"""

# We keep all initialization code in a separate module.

from pystache.init import Renderer, TemplateSpec, parse, render

from ._version import __version__

version = __version__

__all__ = ['parse', 'render', 'Renderer', 'TemplateSpec']
