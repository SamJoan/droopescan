"""
PyTest Fixtures.
"""

import os
import shutil
import pytest
from tempfile import mkstemp, mkdtemp


@pytest.fixture(scope="function")
def tmp(request):
    """
    Create a `tmp` object that geneates a unique temporary directory, and file
    for each test function that requires it.
    """

    class Tmp(object):
        cleanup = True

        def __init__(self):
            self.dir = mkdtemp()
            _, self.file = mkstemp(dir=self.dir)

    t = Tmp()
    yield t

    # cleanup
    if os.path.exists(t.dir) and cleanup is True:
        shutil.rmtree(t.dir)
