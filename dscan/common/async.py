from __future__ import print_function
from base64 import b64encode, b64decode
from dscan.plugins.internal.base_plugin_internal import DEFAULT_UA
from itertools import islice
from twisted.internet import reactor
from twisted.internet import ssl
from twisted.python import log
from twisted.web import client
from twisted.web.iweb import IBodyProducer
from zope.interface.declarations import implementer

# https://stackoverflow.com/questions/18670252/how-to-suppress-noisy-factory-started-stopped-log-messages-from-twisted
client.HTTPClientFactory.noisy = False

REQUEST_DEFAULTS = {
    'timeout': 60,
    'agent': DEFAULT_UA,
    'followRedirect': False
}

def target_get(url, host_header):
    u = client.URI.fromBytes(url)

    headers = {}
    if host_header != None:
        headers['Host'] = host_header
    else:
        headers['Host'] = u.host

    return u, headers

def make_request(u, factory):
    """
    Passes the factory to the reactor. If scheme is HTTPs, request is done over
    HTTPs.
    @param u: client.URI
    @param factory: HttpClientFactory
    """
    if u.scheme == 'https':
        reactor.connectSSL(u.host, u.port, factory, ssl.ClientContextFactory())
    else:
        reactor.connectTCP(u.host, u.port, factory)

def request_url(url, host_header):
    """
    Makes a request to a specified resource with an arbitrary host header,
    without following redirects. Redirects will raise a PageRedirect, errors
    will result in Error exceptions.
    @param url: the URL for the resource.
    @param host_header: value for the HTTP host header. If None, it will be
        obtained from the URL.
    @see twisted.web.error.
    """
    u, headers = target_get(url, host_header)
    kwargs = dict(REQUEST_DEFAULTS)
    kwargs['headers'] = headers

    factory = client.HTTPClientFactory(url, **kwargs)
    make_request(u, factory)

    return factory.deferred

def download_url(url, host_header, filename):
    """
    Downloads a specified URL over HTTP.
    @param url: the URL of the file to download.
    @param host_header: the value for the host header.
    @param filename: location of the file to save.b
    """
    u, headers = target_get(url, host_header)
    kwargs = dict(REQUEST_DEFAULTS)
    kwargs['headers'] = headers

    factory = client.HTTPDownloader(url, filename, **kwargs)
    make_request(u, factory)

    return factory.deferred

def filename_encode(filename):
    """
    Encodes filename in a way that is safe to store in disk. Safe in this
    context means it does not have any special path characters, like "/".
    @param filename: the filename to encode.
    """
    return b64encode(filename)

def filename_decode(filename):
    """
    Reverses filename_encode.
    @param filename: the filename to decode.
    """
    return b64decode(filename)

@implementer(IBodyProducer)
class TargetProducer(client.FileBodyProducer):
    def _writeloop(self, consumer):
        """
        Return an iterator which reads one chunk of bytes from the input file
        and writes them to the consumer for each time it is iterated.
        """
        while True:
            lines = list(islice(self._inputFile, self._readSize))
            if len(lines) == 0:
                self._inputFile.close()
                consumer.finish()
                break

            consumer.write(lines)
            yield None

class TargetConsumer():
    producer = None
    finished = False
    unregistered = True
    importState = None
    lines_processor = None

    def __init__(self, lines_processor):
        self.lines_processor = lines_processor

    def registerProducer(self, producer):
        self.producer = producer

    def unregisterProducer(self):
        self.unregistered = True

    def finish(self):
        log.msg('TargetConsumer finished.')
        reactor.callFromThread(reactor.stop)

    def write(self, lines):
        self.producer.pauseProducing()
        d = self.lines_processor(lines)
        d.addCallback(lambda ignored: self.producer.resumeProducing())

