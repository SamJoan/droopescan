from __future__ import print_function
from dscan.common.async import TargetProducer, TargetConsumer
from dscan.common.exceptions import UnknownCMSException, VersionFingerprintFailed
from dscan.common.output import Output
from functools import partial
from tempfile import mkdtemp
try:
    from twisted.internet import defer
    from twisted.internet import reactor
    from twisted.python.failure import Failure
    from twisted.python import log
    from twisted.web.error import PageRedirect, Error
    from twisted.web import client
except:
    pass
import dscan.common.async as async
import dscan.common.functions as f
import dscan.common.plugins_util as pu
import json
import os
import shutil
import sys

def delete_tempdir(tempdir):
    if os.path.isdir(tempdir):
        shutil.rmtree(tempdir)

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
    def ret_result(results, tempdir, location):
        succ = filter(lambda r: r[0], results)
        if len(succ) == 0:
            msg = "'%s' not identified as any CMS."
            return Failure(UnknownCMSException(msg % str(location)))
        else:
            return tempdir

    def clean(fail, tempdir):
        delete_tempdir(tempdir)
        return fail

    tempdir = mkdtemp(prefix='dscan') + "/"
    required_files = pu.get_rfu()

    ds = []
    for f in required_files:
        url = base_url + f
        download_location = tempdir + async.filename_encode(f)
        d = async.download_url(url, host_header, download_location)
        ds.append(d)

    dl = defer.DeferredList(ds, consumeErrors=True)
    dl.addCallback(ret_result, tempdir, (base_url, host_header))
    dl.addErrback(clean, tempdir)

    return dl

def identify_rfu_easy(tempdir, files_found):
    if len(files_found) > 0:
        cms_found = None
        for plugin, f in files_found:
            plugin_name = plugin.Meta.label
            more_than_one = cms_found != None and cms_found != plugin_name
            if more_than_one:
                cms_found = None
                break

            cms_found = plugin_name

        return cms_found
    else:
        raise UnknownCMSException('Tempdir "%s" was empty.' % tempdir)

def identify_rfu(tempdir):
    """
    Given a temporary directory, attempts to distinguish CMS' from non-CMS
    websites and from each other.

    If a single CMS file is identified, then no hashing is performed and the
    file is assumed to be of that particular CMS. False positives will be weeded
    during the version detection phase.

    If all files requested were responded with 200 OK, the site is discarded.
    This is a design decision I might reconsider if it results in too many false
    negatives.

    @param tempfile: as returned by download_rfu.
    @return: DeferredList
    """
    rfu = pu.get_rfu()
    plugins = pu.plugins_base_get()
    files_found = async.rfu_path(tempdir, plugins)

    if len(rfu) == len(files_found):
        msg = "Url responded 200 OK to everything"
        return defer.fail(UnknownCMSException(msg))

    cms_name = identify_rfu_easy(tempdir, files_found)
    if cms_name:
        return defer.succeed(cms_name)

    return defer.fail(UnknownCMSException("This shouldn't happen too often."))

@defer.inlineCallbacks
def identify_url(base_url, host_header):
    tempdir = yield download_rfu(base_url, host_header)
    try:
        cms_name = yield identify_rfu(tempdir)
        defer.returnValue((cms_name, tempdir))
    except Exception:
        delete_tempdir(tempdir)
        raise

def version_download(base_url, host_header, plugin, tempdir):
    """
    Download files required for hashing.
    """
    def cb(results):
        succ = filter(lambda r: r[0], results)
        if len(succ) == 0:
            msg = "No files downloaded"
            return Failure(VersionFingerprintFailed(msg))
        else:
            return tempdir

    vf = pu.plugin_get_vf(plugin)
    required_files = vf.files_get_all()
    ds = []
    for f in required_files:
        filename = tempdir + async.filename_encode(f)
        if not os.path.isfile(filename):
            d = async.download_url(base_url + f, host_header, filename)
            ds.append(d)

    dl = defer.DeferredList(ds, consumeErrors=True)
    dl.addCallback(cb)
    return dl

def version_hash(plugin, tempdir):
    vf = pu.plugin_get_vf(plugin)
    required_files = vf.files_get_all()

    md5sum_files = []
    for f in required_files:
        filename = tempdir + async.filename_encode(f)
        if os.path.isfile(filename):
            md5sum_files.append(filename)

    d = async.subprocess('/usr/bin/md5sum', md5sum_files)
    return d

def version_get(plugin, stdout):
    vf = pu.plugin_get_vf(plugin)
    hashes = {}
    for line in stdout.split('\n'):
        if line == "":
            continue

        h, f = line.split()
        filename = async.filename_decode(os.path.basename(f))
        hashes[filename] = h

    return vf.version_get(hashes)

@defer.inlineCallbacks
def identify_version_url(base_url, host_header, cms_name, tempdir):
    """
    Finally determines the version of a URL.
    @param base_url: base url.
    @param host_header: value for the "host" header.
    @param cms_name: the name of the CMS this URL has been identified as.
    @param tempdir: a temp dir to write files to.
    """
    try:
        plugin = pu.plugin_get(cms_name)
        yield version_download(base_url, host_header, plugin, tempdir)
        hashes = yield version_hash(plugin, tempdir)
        versions = version_get(plugin, hashes)
        defer.returnValue(versions)
    finally:
        delete_tempdir(tempdir)

@defer.inlineCallbacks
def identify_line(line):
    """
    Asynchronously performs CMS identification on a particular URL. The process
    is as follows:

    - Make a request to the site's root.
        - If 403, 500 or other error code, or connection error, raise.
        - If redirect, change base URL to redirected URL (after repairing the
          URL).
    - For each URL:
        - Request common JS files for all CMS.
        - If files for a single CMS are found, determine that to be the CMS.
        - If server responds with 200 OK to everything, break.
        - If no files for any CMS break.
        - Else, break. (this shouldn't happen too often)
    - Perform version identification:
        - Request all required files and return a deferredlist with a callback.
        - Hash all these files.
        - Use the hashes to calculate the version.

    @param line: the line to identify.
    @return: deferred
    """
    base_url, host_header = f.process_host_line(line)
    base_url = f.repair_url(base_url)

    try:
        yield async.request_url(base_url, host_header)
    except PageRedirect as e:
        base_url, host_header = f.repair_url(e.location), None

    cms_name, tempdir = yield identify_url(base_url, host_header)
    versions = yield identify_version_url(base_url, host_header, cms_name, tempdir)

    out = Output()
    out.host = (base_url, host_header)
    out.version = versions

    print(json.dumps(out.__dict__))

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
