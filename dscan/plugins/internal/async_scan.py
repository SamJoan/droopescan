from __future__ import print_function
from dscan.common.async import request_url, download_url
from dscan.common.async import TargetProducer, TargetConsumer
from functools import partial
from twisted.internet import defer
from twisted.internet import reactor
from twisted.python import log
from twisted.web.error import PageRedirect, Error
from twisted.web import client
from tempfile import mkdtemp
import dscan.common.functions as f
import dscan.common.plugins_util as pu
import sys
import base64

def error_line(line, failure):
    """
    High-level error handler for most errors within the main loop.
    @param line: the full line where the error occured.
    @param failure: the failure passed to the errback.
    @return:
    """
    log.err(failure, "Line '%s' raised" % line.rstrip())

def download_rfu(base_url, host_header):
    """
    Download all "regular file urls" for all CMS.
    @param base_url:
    @param host_header:
    @return DeferredList
    """
    def ignore_non_success(f):
        f.trap(Error)

    def ret_result(ign, tempdir):
        return tempdir

    tempdir = mkdtemp(prefix='dscan')
    files_required = pu.get_rfu()

    ds = []
    for f in files_required:
        url = base_url + f
        download_location = tempdir + "/" + base64.b64encode(f)
        d = download_url(url, host_header, download_location)
        d.addErrback(ignore_non_success)
        ds.append(d)

    dl = defer.DeferredList(ds)
    dl.addCallback(ret_result, tempdir)
    return dl

@defer.inlineCallbacks
def identify_url(base_url, host_header):
    tempfile = yield download_rfu(base_url, host_header)

@defer.inlineCallbacks
def identify_line(line):
    """
    Asynchronously performs CMS identification on a particular URL. The process
    is as follows:

    - Make a request to the site's root.
        - If 403, 500 or other error code, or connection error, raise.
        - If redirect, change base URL to redirected URL (after repairing the
          URL).
    - For each CMS(ordered by popularity):
        - Make a request for known files
            - If files exist and are an expected value, break.
            - If files do not exist or are not as expected, continue.
        - If no CMS identified, raise.
    - Perform version identification:
        - Request all required files and return a deferredlist with a callback.
        - Hash all these files and return version information.

    @param line: the line to identify.
    @return: deferred
    """
    base_url, host_header = f.process_host_line(line)
    base_url = f.repair_url(base_url)

    try:
        yield request_url(base_url, host_header)
    except PageRedirect as e:
        base_url, host_header = f.repair_url(e.location), None

    cms_name = yield identify_url(base_url, host_header)

def identify_lines(lines):
    """
    Calls identify_url on all lines provided, after stripping whitespace.
    @return: defer.DeferredList
    """
    ds = []
    for line in lines:
        d = identify_line(line)
        d.addErrback(partial(error_line, line))
        ds.append(d)

    dl = defer.DeferredList(ds)
    return dl

def _identify_url_file(fh):
    """
    Performs a scan over each individual line of file, utilising twisted. This
    provides better performance for mass-scanning, so it is provided as an
    option.

    Behaviour should be mostly similar to the regular mass-identify, although
    with defaults set for mass-scanning.

    @param fh: a file handle. Upon finishing, this will be closed by this
    function.
    """
    target_producer = TargetProducer(fh, readSize=1000)
    target_consumer = TargetConsumer(lines_processor=identify_lines)

    target_consumer.registerProducer(target_producer)
    target_producer.startProducing(target_consumer)

def identify_url_file(*args, **kwargs):
    """
    @see: _identify_url_file()
    """
    log.startLogging(sys.stdout)
    _identify_url_file(*args, **kwargs)
    reactor.run()

if __name__ == '__main__':
    identify_url_file(sys.argv)
