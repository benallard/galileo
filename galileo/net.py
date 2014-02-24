
import base64
import random
import StringIO

import xml.etree.ElementTree as ET

import logging
logger = logging.getLogger(__name__)

import requests

from . import __version__
from .utils import s2a


class SyncError(Exception):
    def __init__(self, errorstring='Undefined'):
        self.errorstring = errorstring


class BackOffException(Exception):
    def __init__(self, min, max):
        self.min = min
        self.max = max

    def getAValue(self):
        return random.randint(self.min, self.max)


def toXML(name, attrs={}, childs=[], body=None):
    elem = ET.Element(name, attrib=attrs)
    if childs:
        elem.extend(tuplesToXML(childs))
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


class GalileoClient(object):
    ID = '6de4df71-17f9-43ea-9854-67f842021e05'

    def __init__(self, url):
        self.url = url

    def post(self, mode, dongle=None, data=None):
        client = toXML('galileo-client', {'version': "2.0"})
        info = toXML('client-info', childs=[
            ('client-id', {}, [], self.ID),
            ('client-version', {}, [], __version__),
            ('client-mode', {}, [], mode)])
        if dongle is not None:
            info.append(toXML(
                'dongle-version',
                {'major': str(dongle.major),
                 'minor': str(dongle.minor)}))
        client.append(info)
        if data is not None:
            client.extend(tuplesToXML(data))

        f = StringIO.StringIO()

        tree = ET.ElementTree(client)
        tree.write(f, xml_declaration=True, encoding="UTF-8")

        logger.debug('HTTP POST=%s', f.getvalue())
        r = requests.post(self.url,
                          data=f.getvalue(),
                          headers={"Content-Type": "text/xml"})
        r.raise_for_status()

        logger.debug('HTTP response=%s', r.text)

        tag, attrib, childs, body = XMLToTuple(ET.fromstring(r.text))

        if tag != 'galileo-server':
            logger.error("Unexpected root element: %s", tag)

        if attrib['version'] != "2.0":
            logger.error("Unexpected server version: %s",
                         attrib['version'])

        for child in childs:
            stag, _, schilds, sbody = child
            if stag == 'error':
                raise SyncError(sbody)
            elif stag == 'back-off':
                minD = 0
                maxD = 0
                for schild in schilds:
                    sstag, _, _, ssbody = schild
                    if sstag == 'min': minD = int(ssbody)
                    if sstag == 'max': maxD = int(ssbody)
                raise BackOffException(minD, maxD)

        return childs

    def requestStatus(self):
        self.post('status')

    def sync(self, dongle, trackerId, megadump):
        server = self.post('sync', dongle, (
            'tracker', {'tracker-id': trackerId}, (
                'data', {}, [], megadump.toBase64())))

        tracker = None
        for elem in server:
            if elem[0] == 'tracker':
                tracker = elem
                break

        if tracker is None:
            raise SyncError('no tracker')

        _, a, c, _ = tracker
        if a['tracker-id'] != trackerId:
            logger.error('Got the response for tracker %s, expected tracker %s',
                         a['tracker-id'], trackerId)
        if a['type'] != 'megadumpresponse':
            logger.error('Not a megadumpresponse: %s', a['type'])

        if not c:
            raise SyncError('no data')
        if len(c) != 1:
            logger.error("Unexpected childs length: %d", len(c))
        t, _, _, d = c[0]
        if t != 'data':
            raise SyncError('not data: %s' % t)

        return s2a(base64.b64decode(d))
