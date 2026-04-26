import os
import sys

# Make the vendored, Python 3.13-compatible copy of ``cement`` importable
# as the top-level ``cement`` package. Cement 2.x is unmaintained and used
# the ``imp`` module which was removed in Python 3.12; the vendored copy in
# ``dscan/vendor/cement`` has been ported to :mod:`importlib`.
_VENDOR_DIR = os.path.join(os.path.dirname(__file__), "vendor")
if _VENDOR_DIR not in sys.path:
    sys.path.insert(0, _VENDOR_DIR)

PWD = os.path.dirname(__file__) + "/"
