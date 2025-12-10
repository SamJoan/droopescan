# encoding: utf-8

"""
This module contains the initialization logic called by __init__.py.

"""

# do not let linter tools remove any imports !!
from pystache.parser import parse  # noqa
from pystache.renderer import Renderer
from pystache.template_spec import TemplateSpec  # noqa


def render(template, context=None, **kwargs):
    """
    Return the given template string rendered using the given context.

    """
    renderer = Renderer()
    return renderer.render(template, context, **kwargs)
