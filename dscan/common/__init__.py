from __future__ import print_function

# Kept for backwards compatibility.
from dscan.common.enum import Enumerate, ScanningMethod, colors, ValidOutputs, Verb
from dscan.common.functions import base_url, dict_combine, enum_list, file_len, in_enum, \
    is_string, md5_file, scan_http_status, strip_letters, strip_whitespace, \
    template, repair_url, version_gt
from dscan.common.output import JsonOutput, ProgressBar, SmartFormatter, \
        StandardOutput, RequestsLogger
from dscan.common.versions import VersionsFile
import logging

# Global shutdown variable used to manage Ctrl + C.
shutdown = False

logging.basicConfig(level=logging.WARN)
logger = logging.getLogger(__name__)
