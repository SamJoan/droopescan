from __future__ import print_function
from twisted.internet import defer
from twisted.internet import reactor
from twisted.python import log
from twisted.web.error import PageRedirect, Error
from twisted.web import client
from dscan.common.async import request_url
from dscan.common.async import TargetProducer, TargetConsumer, LineError
import sys

@defer.inlineCallbacks
def identify_line(line):
    """
    Asynchronously performs CMS identification on a particular URL.
    @param line: the line to identify.
    @return: deferred
    """
    base_url = line.strip()
    try:
        yield request_url(base_url)
    except PageRedirect as e:
        base_url = e.location

def identify_lines(lines):
    """
    Calls identify_url on all lines provided, after stripping whitespace.
    @return: defer.DeferredList
    """
    ds = []
    for line in lines:
        d = identify_line(line)

        l = LineError(line)
        d.addErrback(l.error_line)

        ds.append(d)

    dl = defer.DeferredList(ds)
    return dl

def _identify_url_file(url_file):
    """
    Performs a scan over each individual line of file, utilising twisted. This
    provides better performance for mass-scanning, so it is provided as an
    option.

    Behaviour should be mostly similar to the regular mass-identify, although
    with defaults set for mass-scanning.

    @param url_file: the url_file to scan.
    """
    import os
    print(os.getcwd())
    fh = open(url_file)

    target_producer = TargetProducer(fh, readSize=1000)
    target_consumer = TargetConsumer(lines_processor=identify_lines)

    target_consumer.registerProducer(target_producer)
    target_producer.startProducing(target_consumer)

    pass

def identify_url_file(*args, **kwargs):
    """
    @see: _identify_url_file()
    """
    log.startLogging(sys.stdout)
    _identify_url_file(*args, **kwargs)
    reactor.run()

if __name__ == '__main__':
    identify_url_file(sys.argv)
