from inspect import getmembers, isfunction, ismethod
from lxml import etree
import dscan
import inspect

def decallmethods(decorator, prefix='test_'):
    """
    Decorates all methods in class which begin with prefix test_ to prevent
    accidental external HTTP requests.
    """
    def dectheclass(cls):
        for name, m in getmembers(cls, predicate=lambda x: isfunction(x)
                or ismethod(x)):

            if name.startswith(prefix):
                setattr(cls, name, decorator(m))

        return cls

    return dectheclass

def _validate(xmlparser, xmlfilename):
    """
    Raises an exception if the XML file doesn't validate.
    """
    with open(xmlfilename, 'rb') as f:
        etree.fromstring(f.read(), xmlparser)

def xml_validate(xml_file, xsd_file):
    with open(xsd_file, 'rb') as f:
        schema_root = etree.XML(f.read())

    schema = etree.XMLSchema(schema_root)
    xmlparser = etree.XMLParser(schema=schema)

    return _validate(xmlparser, xml_file)

class MockBuffer():
    string = ""

    def write(self, data):
        self.string += data

    def flush(self):
        pass

    def __repr__(self):
        return self.string

    def get(self):
        return self.string

