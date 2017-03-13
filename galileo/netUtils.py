
import random
import socket

import xml.etree.ElementTree as ET

import logging
logger = logging.getLogger(__name__)

class BackOffException(Exception):
    def __init__(self, min, max):
        self.min = min
        self.max = max

    def getAValue(self):
        return random.randint(self.min, self.max)


def toXML(name, attrs={}, childs=[], body=None):
    elem = ET.Element(name, attrib=attrs)
    if childs:
        for XMLElem in tuplesToXML(childs):
            elem.append(XMLElem)
    if body is not None:
        elem.text = body
    return elem


def tuplesToXML(tuples):
    """ tuples is an array (or not) of (name, attrs, childs, body) """
    if isinstance(tuples, tuple):
        tuples = [tuples]
    for tpl in tuples:
        yield toXML(*tpl)


def XMLToTuple(elem):
    """ Transform an XML element into the following tuple:
    (tagname, attributes, subelements, text) where:
     - tagname is the element tag as string
     - attributes is a dictionnary of the element attributes
     - subelements are the sub elements as an array of tuple
     - text is the content of the element, as string or None if no content is
       there
    """
    childs = []
    for child in elem:
        childs.append(XMLToTuple(child))
    return elem.tag, elem.attrib, childs, elem.text


def ConnectionErrorToMessage(ce):
    excpt = ce.args[0]
    if isinstance(excpt, socket.error):
        return excpt.reason.strerror
    return 'ConnectionError'
