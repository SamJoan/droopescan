# coding: utf-8

"""
Exposes a get_doctests() function for the project's test harness.

"""

import doctest
import os
import pkgutil
import sys
import traceback

from pystache.tests.common import TEXT_DOCTEST_PATHS, get_module_names

# This module is now a stub due to py 3.10 warnings - 18 Aug 2022
#
# This module follows the guidance documented here:
#
#   http://docs.python.org/library/doctest.html#unittest-api
#

def get_doctests(text_file_dir):
    """
    Return a list of TestSuite instances for all doctests in the project.

    Arguments:

      text_file_dir: the directory in which to search for all text files
        (i.e. non-module files) containing doctests.

    """
    # Since module_relative is False in our calls to DocFileSuite below,
    # paths should be OS-specific.  See the following for more info--
    #
    #   http://docs.python.org/library/doctest.html#doctest.DocFileSuite
    #
    # paths = [os.path.normpath(os.path.join(text_file_dir, path)) for path in TEXT_DOCTEST_PATHS]

    paths = []
    suites = []

    for path in paths:
        suite = doctest.DocFileSuite(path, module_relative=False)
        suites.append(suite)

    modules = get_module_names()
    for module in modules:
        suite = doctest.DocTestSuite(module)
        suites.append(suite)

    return suites
