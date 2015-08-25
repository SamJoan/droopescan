from __future__ import print_function
from twisted.internet import defer
from twisted.internet import reactor
from twisted.python import log
from twisted.web.error import PageRedirect, Error
from twisted.web import client
from util import request_url
from util import TargetProducer, TargetConsumer, LineError
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

def main(argv):
    log.startLogging(sys.stdout)

    filename = sys.argv[1]
    fh = open(filename)

    target_producer = TargetProducer(fh, readSize=1000)
    target_consumer = TargetConsumer(lines_processor=identify_lines)

    target_consumer.registerProducer(target_producer)
    target_producer.startProducing(target_consumer)

    reactor.run()

if __name__ == '__main__':
    main(sys.argv)
