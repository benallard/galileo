#!/usr/bin/env python
"""\
galileo.py Utility to synchronize a fitbit tracker with the fitbit server.

Copyright (C) 2013-2014 Benoit Allard
Copyright (C) 2014 Stuart Hickinbottom
"""

import usb.core

import xml.etree.ElementTree as ET

import requests

import base64

import argparse

import yaml

import logging

import time
import os
import sys
import errno
import StringIO

# Module-level logging.
logger = logging.getLogger(__name__)

from ctypes import c_byte

__version__ = '0.4dev'

MICRODUMP = 3
MEGADUMP = 13

DEFAULT_RCFILE_NAME = "~/.galileorc"

def a2x(a, delim=' ', shorten=False):
    """ array to string of hexa
    delim is the delimiter between the hexa
    shorten don't print the trailing zeros
    """
    shortened = 0
    if shorten:
        while a[-1] == 0:
            shortened += 1
            del a[-1]
    s = ''
    if shortened:
        s = ' 00 (%d times)' % shortened
    return delim.join('%02X' % x for x in a) + s

def s2x(s):
    """ string to string of hexa """
    return ' '.join('%02X' % ord(c) for c in s)

def a2s(a, toPrint=True):
    """ array to string
    toPrint indicates that the resulting string is to be printed (stop at the
    first \0)
    """
    s = []
    for c in a:
        if toPrint and (c == 0):
            break
        s.append(chr(c))
    return ''.join(s)

def s2a(s):
    """ string to array """
    return [ord(c) for c in s]

class USBDevice(object):
    def __init__(self, vid, pid):
        self.vid = vid
        self.pid = pid
        self._dev = None

    @property
    def dev(self):
        if self._dev is None:
            self._dev = usb.core.find(idVendor=self.vid, idProduct=self.pid)
        return self._dev

    def __del__(self):
        pass

class DataMessage(object):
    length = 32
    def __init__(self, data, out=True):
        if out: # outgoing
            if len(data) > 31:
                raise ValueError('data %s (%d) too big' % (data, len(data)))
            self.data = data
            self.len = len(data)
        else: # incoming
            if len(data) != 32:
                raise ValueError('data %s with wrong length' % data)
            # last byte is length
            self.len = data[-1]
            self.data = list(data[:self.len])

    def asList(self):
        return self.data + [0]*(31 - self.len) + [self.len]

    def __str__(self):
        return ' '.join(['[', a2x(self.data), ']', '-', str(self.len)])

DM = DataMessage

def unSLIP1(data):
    """ The protocol uses a particular version of SLIP (RFC 1055) applied
    only on the first byte of the data"""
    END = 0300
    ESC = 0333
    ESC_ = {0334: END,
            0335: ESC}
    if data[0] == ESC:
        return [ESC_[data[1]]] + data[2:]
    return data

def isATimeout(excpt):
    if excpt.errno == errno.ETIMEDOUT:
        return True
    elif excpt.errno is None and excpt.args == ('Operation timed out',):
        return True
    else:
        return False

class NoDongleException(Exception): pass

class TimeoutError(Exception): pass

class DongleWriteException(Exception): pass

class PermissionDeniedException(Exception): pass

class FitBitDongle(USBDevice):
    VID = 0x2687
    PID = 0xfb01

    def __init__(self):
        USBDevice.__init__(self, self.VID, self.PID)

    def setup(self):
        if self.dev is None:
            raise NoDongleException()

        try:
            if self.dev.is_kernel_driver_active(0):
                self.dev.detach_kernel_driver(0)
            if self.dev.is_kernel_driver_active(1):
                self.dev.detach_kernel_driver(1)
        except usb.core.USBError, ue:
            if ue.errno == errno.EACCES:
                logger.error('Insufficient permissions to access the Fitbit dongle')
                raise PermissionDeniedException
            raise

        cfg = self.dev.get_active_configuration();
        self.DataIF = cfg[(0, 0)]
        self.CtrlIF = cfg[(1, 0)]
        self.dev.set_configuration()

    def ctrl_write(self, data, timeout=2000):
        logger.debug('--> %s', a2x(data))
        l = self.dev.write(0x02, data, self.CtrlIF.bInterfaceNumber, timeout=timeout)
        if l != len(data):
            logger.error('Bug, sent %d, had %d', l, len(data))
            raise DongleWriteException

    def ctrl_read(self, timeout=2000, length=32):
        try:
            data = self.dev.read(0x82, length, self.CtrlIF.bInterfaceNumber, timeout=timeout)
        except usb.core.USBError, ue:
            if isATimeout(ue):
                raise TimeoutError
            raise
        if list(data[:2]) == [0x20, 1]:
            logger.debug('<-- %s %s', a2x(data[:2]), a2s(data[2:]))
        else:
            logger.debug('<-- %s', a2x(data, shorten=True))
        return data


    def data_write(self, msg, timeout=2000):
        logger.debug('==> %s', msg)
        l = self.dev.write(0x01, msg.asList(), self.DataIF.bInterfaceNumber, timeout=timeout)
        if l != 32:
            logger.error('Bug, sent %d, had 32', l)
            raise DongleWriteException

    def data_read(self, timeout=2000):
        try:
            data = self.dev.read(0x81, 32, self.DataIF.bInterfaceNumber, timeout=timeout)
        except usb.core.USBError, ue:
            if isATimeout(ue):
                raise TimeoutError
            raise
        msg = DM(data, out=False)
        logger.debug('<== %s', msg)
        return msg


class Tracker(object):
    def __init__(self, Id, addrType, serviceUUID, syncedRecently):
        self.id = Id
        self.addrType = addrType
        self.serviceUUID = serviceUUID
        self.syncedRecently = syncedRecently


class FitbitClient(object):
    def __init__(self, dongle):
        self.dongle = dongle

    def disconnect(self):
        logger.info('Disconnecting from any connected trackers')

        self.dongle.ctrl_write([2, 2])
        self.dongle.ctrl_read() # CancelDiscovery
        self.dongle.ctrl_read() # TerminateLink

        try:
            # It is OK to have a timeout with the following ctrl_read as
            # they are there to clean up any connection left open from
            # the previous attempts.
            self.dongle.ctrl_read()
            self.dongle.ctrl_read()
            self.dongle.ctrl_read()
        except TimeoutError:
            # assuming link terminated
            pass

    def getDongleInfo(self):
        try:
            self.dongle.ctrl_write([2, 1, 0, 0x78, 1, 0x96])
            d = self.dongle.ctrl_read()
            self.major = d[2]
            self.minor = d[3]
            logger.debug('Fitbit dongle version major:%d minor:%d', self.major, self.minor)
        except TimeoutError:
            logger.error('Failed to get connected Fitbit dongle information')
            raise

    def discover(self):
        self.dongle.ctrl_write([0x1a, 4, 0xba, 0x56, 0x89, 0xa6, 0xfa, 0xbf,
                           0xa2, 0xbd, 1, 0x46, 0x7d, 0x6e, 0, 0,
                           0xab, 0xad, 0, 0xfb, 1, 0xfb, 2, 0xfb,
                           0xa0, 0x0f, 0, 0xd3, 0, 0, 0, 0])
        self.dongle.ctrl_read() # StartDiscovery
        d = self.dongle.ctrl_read(10000)
        while d[0] != 3:
            trackerId = list(d[2:8])
            addrType = d[8]
            RSSI = c_byte(d[9]).value
            attributes = list(d[11:13])
            syncedRecently = (d[12] != 4)
            serviceUUID = list(d[17:19])
            logger.debug('Tracker: %s, %s, %s, %s (%s), %s', trackerId, addrType, RSSI, attributes, syncedRecently, serviceUUID)
            if not syncedRecently:
                logger.debug('Tracker %s was not recently synchronized', a2x(trackerId, delim=""))
            if RSSI < -80:
                logger.info("Tracker %s has low signal power (%ddBm), higher chance of"\
                    " miscommunication", a2x(trackerId, delim=""), RSSI)
            yield Tracker(trackerId, addrType, serviceUUID, syncedRecently)
            d = self.dongle.ctrl_read(4000)

        # tracker found, cancel discovery
        self.dongle.ctrl_write([2, 5])
        self.dongle.ctrl_read() # CancelDiscovery

    def establishLink(self, tracker):
        self.dongle.ctrl_write([0xb, 6]+tracker.id+[tracker.addrType]+tracker.serviceUUID)
        self.dongle.ctrl_read() # EstablishLink
        self.dongle.ctrl_read(5000)
        # established, waiting for service discovery
        # - This one takes long
        self.dongle.ctrl_read(8000) # GAP_LINK_ESTABLISHED_EVENT
        self.dongle.ctrl_read()

    def enableTxPipe(self):
        # enabling tx pipe
        self.dongle.ctrl_write([3, 8, 1])
        self.dongle.data_read(5000)

    def initializeAirlink(self):
        self.dongle.data_write(DM([0xc0, 0xa, 0xa, 0, 6, 0, 6, 0, 0, 0, 0xc8, 0]))
        self.dongle.ctrl_read(10000)
        self.dongle.data_read()

    def getDump(self, dumptype=MEGADUMP):
        logger.debug('Getting dump type %d', dumptype)

        # begin dump of appropriate type
        self.dongle.data_write(DM([0xc0, 0x10, dumptype]))
        r = self.dongle.data_read()
        assert r.data == [0xc0, 0x41, dumptype], r.data

        dump = []
        # megadump body
        d = self.dongle.data_read()
        dump.extend(d.data)
        while d.data[0] != 0xc0:
            d = self.dongle.data_read()
            dump.extend(unSLIP1(d.data))
        # megadump footer
        dataType = d.data[2]
        assert dataType == dumptype, "%x != %x" % (dataType, dumptype)
        nbBytes = d.data[6] * 0xff + d.data[5]
        transportCRC = d.data[3] * 0xff + d.data[4]
        esc1 = d.data[7]
        esc2 = d.data[8]
        logger.debug('Dump done. length %d, embedded length %d', len(dump), nbBytes)
        logger.debug('transportCRC=0x%04x, esc1=0x%02x, esc2=0x%02x', transportCRC, esc1, esc2)
        return dump

    def uploadResponse(self, response):
        self.dongle.data_write(DM([0xc0, 0x24, 4]+[len(response)&0xff, len(response)>> 8]+[0, 0, 0, 0]))
        self.dongle.data_read()

        for i in range(0,len(response), 20):
            self.dongle.data_write(DM(response[i:i+20]))
            self.dongle.data_read()

        self.dongle.data_write(DM([0xc0, 2]))
        self.dongle.data_read(60000) # This one can be very long. He is probably erasing the memory there
        self.dongle.data_write(DM([0xc0, 1]))
        self.dongle.data_read()

    def disableTxPipe(self):
        self.dongle.ctrl_write([3, 8])
        self.dongle.data_read(5000)

    def terminateAirlink(self):
        self.dongle.ctrl_write([2, 7])
        self.dongle.ctrl_read() # TerminateLink

        self.dongle.ctrl_read()
        self.dongle.ctrl_read() # GAP_LINK_TERMINATED_EVENT
        self.dongle.ctrl_read() # 22


class SyncError(Exception):
    def __init__(self, errorstring='Undefined'):
        self.errorstring = errorstring

def toXML(name, attrs={}, childs=[], body=None):
    elem = ET.Element(name, attrib=attrs)
    if childs:
        elem.extend(tuplesToXML(childs))
    if body is not None:
        elem.text=body
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
                          data= f.getvalue(),
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
            stag, _, _, sbody = child
            if stag == 'error':
                raise SyncError(sbody)

        return childs

    def requestStatus(self):
        self.post('status')

    def sync(self, dongle, trackerId, megadump):
        server = self.post('sync', dongle, (
            'tracker', {'tracker-id': trackerId}, (
                'data', {}, [], base64.b64encode(a2s(megadump, False)))))

        tracker = None
        for elem in server:
            if elem[0] == 'tracker':
                tracker=elem
                break

        if tracker is None:
            raise SyncError('no tracker')

        _, a, c, _ = tracker
        if a['tracker-id'] != trackerId:
            logger.error('Got the response for tracker %s, expected tracker %s', a['tracker-id'], trackerId)
        if a['type'] != 'megadumpresponse':
            logger.error('Not a megadumpresponse: %s', a['type'])

	if len(c) != 1:
            logger.error("Unexpected childs length: %d", len(c))
        t, _, _, d = c[0]
        if t != 'data':
            raise SyncError('no data')

        return s2a(base64.b64decode(d))

class Config(object):
    """Class holding the configuration to be applied during synchronization.
    The configuration can be loaded from a file in which case the defaults
    can be overridden; loading from multiple files allows the settings from
    later files to override those defined in earlier files. Finally, each
    configuration option can also be set directly, which is used to allow
    overriding of file-based configuration settings with those explicitly
    specified on the command line.
    """
    DEFAULT_DUMP_DIR = "~/.galileo"
    def __init__(self):
        self.__logLevelMap = { 'default': logging.WARNING,
                               'verbose': logging.INFO,
                               'debug': logging.DEBUG }
        self.__logLevelMapReverse = {}
        for key in self.__logLevelMap:
            self.__logLevelMapReverse[self.__logLevelMap[key]] = key
        self.__logLevel = logging.WARNING
        self._includeTrackers = None
        self._excludeTrackers = ()
        self._keepDumps = True
        self._dumpDir = self.DEFAULT_DUMP_DIR
        self._doUpload = True
        self._forceSync = False

    # Property accessors and definitions
    @property
    def logLevel(self):
        """Logging level. Values are as defined in Logging.setLevel() and can
        be set as an integer or string.

        """
        return self.__logLevel
    @logLevel.setter
    def logLevel(self, value):
        if isinstance(value, basestring):
            self.__logLevel = self.__logLevelMap[str(value).lower()]
        else:
            self.__logLevel = value
    @property
    def keepDumps(self):
        """Flag indicate data from tracker should be saved."""
        return self._keepDumps
    @keepDumps.setter
    def keepDumps(self, value): self._keepDumps = value
    @property
    def includeTrackers(self):
        """List of trackers to synchronize, or None for to synchronize all.
        Can be set via a comma-separated list string or from a list.

        """
        return self._includeTrackers
    @includeTrackers.setter
    def includeTrackers(self, value):
        if isinstance(value, basestring):
            self._includeTrackers = value.split(',')
        else:
            self._includeTrackers = value
        # Now make sure the list of trackers is all in lower-case to
        # make comparisons easier later.
        if self._includeTrackers is not None:
            self._includeTrackers = [str(x).upper() for x in self._includeTrackers]
    @property
    def excludeTrackers(self):
        """List of trackers to avoid synchronizing. Can be set via a
        comma-separated list string or from a list.

        """
        return self._excludeTrackers
    @excludeTrackers.setter
    def excludeTrackers(self, value):
        if isinstance(value, basestring):
            self._excludeTrackers = value.split(',')
        else:
            self._excludeTrackers = value
        # Now make sure the list of trackers is all in lower-case to
        # make comparisons easier later.
        if self._excludeTrackers is not None:
            self._excludeTrackers = [str(x).upper() for x in self._excludeTrackers]
    @property
    def dumpDir(self):
        """Directory where tracker data should be saved."""
        return self._dumpDir
    @dumpDir.setter
    def dumpDir(self, value): self._dumpDir = value
    @property
    def doUpload(self):
        """Flag indicating whether data from trackers should be uploaded."""
        return self._doUpload
    @doUpload.setter
    def doUpload(self, value): self._doUpload = value
    @property
    def forceSync(self):
        """Flag indicating whether trackers should be synchronized even if
        recently synchronized.

        """
        return self._forceSync
    @forceSync.setter
    def forceSync(self, value): self._forceSync = value

    def __str__(self):
        return ("Config: logLevel = %s, " +
                "keepDumps = %s, " +
                "includeTrackers = %s, " +
                "excludeTrackers = %s, " +
                "dumpDir = %s, " +
                "doUpload = %s, " +
                "forceSync = %s") % (
                    self.__logLevelMapReverse[self.__logLevel],
                    self._keepDumps,
                    self._includeTrackers,
                    self._excludeTrackers,
                    self._dumpDir,
                    self._doUpload,
                    self._forceSync)

def syncAllTrackers(config):
    logger.debug('%s initialising', os.path.basename(sys.argv[0]))
    dongle = FitBitDongle()
    try:
      dongle.setup()
    except NoDongleException:
      logger.error("No dongle connected, aborting")
      return (0, 0, 0)

    fitbit = FitbitClient(dongle)

    galileo = GalileoClient('https://client.fitbit.com/tracker/client/message')

    fitbit.disconnect()

    fitbit.getDongleInfo()

    try:
        logger.info('Discovering trackers to synchronize')
        trackers = [t for t in fitbit.discover()]
    except TimeoutError:
        logger.debug('Timeout trying to discover trackers')
        trackers = []

    trackerssyncd = 0
    trackersskipped = 0
    trackercount = len(trackers)
    logger.info('%d trackers discovered', trackercount)
    for tracker in trackers:
        logger.debug('Discovered tracker with ID %s', a2x(tracker.id, delim=""))

    for tracker in trackers:

        trackerid = a2x(tracker.id, delim="")

        # If a list of trackers to sync was provided then ignore this
        # tracker if it's not in that list.
        if (config['include-trackers'] is not None) and (trackerid not in config['include-trackers']):
            logger.info('Tracker %s is not in the include list; skipping', trackerid)
            trackersskipped += 1
            continue

        # If a list of trackers to avoid syncing was provided then
        # ignore this tracker if it is in that list.
        if trackerid in config['exclude-trackers']:
            logger.info('Tracker %s is in the exclude list; skipping', trackerid)
            trackersskipped += 1
            continue

        if tracker.syncedRecently and config['force-sync']:
            logger.info('Tracker %s was recently synchronized, but forcing synchronization anyway', trackerid)
        elif tracker.syncedRecently:
            logger.info('Tracker %s was recently synchronized; skipping for now', trackerid)
            trackersskipped += 1
            continue

        logger.info('Attempting to synchronize tracker %s', trackerid)

        try:
            logger.debug('Connecting to Fitbit server and requesting status')
            galileo.requestStatus()
        except requests.exceptions.ConnectionError:
            # No internet connection or fitbit server down
            logger.error('Not able to connect to the Fitbit server. Check your internet connection')
            return

        try:
            logger.debug('Establishing link with tracker')
            fitbit.establishLink(tracker)
            fitbit.enableTxPipe()
            fitbit.initializeAirlink()
        except TimeoutError:
            logger.debug('Timeout while trying to establish link with tracker')
            logger.warning('Unable to establish link with tracker %s. Skipping it.', trackerid)
            # tracker was known, but disappeared in the meantime
            continue

        logger.info('Getting data from tracker')
        dump = fitbit.getDump()

        if config['keep-dumps']:
            # Write the dump somewhere for archiving ...
            dirname = os.path.expanduser(os.path.join(config['dump-dir'], trackerid))
            if not os.path.exists(dirname):
                logger.debug("Creating non-existent directory for dumps %s", dirname)
                os.makedirs(dirname)

            filename = os.path.join(dirname, 'dump-%d.txt' % int(time.time()))
            logger.debug("Dumping megadump to %s", filename)
            with open(filename, 'wt') as dumpfile:
                for i in range(0, len(dump), 20):
                    dumpfile.write(a2x(dump[i:i+20])+'\n')
        else:
            logger.debug("Not dumping anything to disk")

        if not config['do-upload']:
            logger.info("Not uploading, as asked ...")
        else:
            try:
                logger.info('Sending tracker data to Fitbit')
                response = galileo.sync(fitbit, trackerid, dump)

                if config['keep-dumps']:
                    logger.debug("Appending answer from server to %s", filename)
                    with open(filename, 'at') as dumpfile:
                        dumpfile.write('\n')
                        for i in range(0, len(response), 20):
                            dumpfile.write(a2x(response[i:i+20])+'\n')

                # Even though the next steps might fail, fitbit has accepted
                # the data at this point.
                trackerssyncd += 1
                logger.info('Successfully sent tracker data to Fitbit')

                try:
                    logger.info('Passing Fitbit response to tracker')
                    fitbit.uploadResponse(response)
                except TimeoutError:
                    logger.warning('Timeout error while trying to give Fitbit response to tracker %s', trackerid)

            except SyncError, e:
                logger.error('Fitbit server refused data from tracker %s, reason: %s', trackerid, e.errorstring)

        try:
            logger.debug('Disconnecting from tracker')
            fitbit.disableTxPipe()
            fitbit.terminateAirlink()
        except TimeoutError:
            logger.warning('Timeout while trying to disconnect from tracker %s', trackerid)

    return (trackercount, trackerssyncd, trackersskipped)

PERMISSION_DENIED_HELP = """
To be able to run the fitbit utility as a non-privileged user, you first
should install a 'udev rule' that lower the permissions needed to access the
fitbit dongle. In order to do so, as root, create the file
/etc/udev/rules.d/99-fitbit.rules with the following content (in one line):

SUBSYSTEM=="usb", ATTR{idVendor}=="%(VID)x", ATTR{idProduct}=="%(PID)x", SYMLINK+="fitbit", MODE="0666"

The dongle must then be removed and reinserted to receive the new permissions.""" % {
	'VID': FitBitDongle.VID, 'PID': FitBitDongle.PID}

def main():
    """ This is the entry point """
    # Define and parse command-line arguments.
    argparser = argparse.ArgumentParser(description="synchronize Fitbit trackers with Fitbit web service",
                                        epilog="""Access your synchronized data at http://www.fitbit.com.""")
    argparser.add_argument("-V", "--version",
                           action="version", version="%(prog)s " + __version__,
                           help="show version and exit")
    argparser.add_argument("-c", "--config",
                            nargs=1, metavar="FILE", dest="rcconfigname",
                            help="use alternative configuration file (defaults to '%s')" % DEFAULT_RCFILE_NAME)
    argparser.add_argument("--dump-dir",
                            nargs=1, metavar="DIR", dest="dump_dir",
                            help="directory for storing dumps (defaults to '%s')" % Config.DEFAULT_DUMP_DIR)
    verbosity_arggroup = argparser.add_argument_group("progress reporting control")
    verbosity_arggroup2 = verbosity_arggroup.add_mutually_exclusive_group()
    verbosity_arggroup2.add_argument("-v", "--verbose",
                                     action="store_true",
                                     help="display synchronization progress")
    verbosity_arggroup2.add_argument("-d", "--debug",
                                     action="store_true",
                                     help="show internal activity (implies verbose)")
    verbosity_arggroup2.add_argument("-s", "--silent",
                                     action="store_true",
                                     help="only show errors and summary (default)")
    force_arggroup = argparser.add_argument_group("force synchronization control")
    force_arggroup2 = force_arggroup.add_mutually_exclusive_group()
    force_arggroup2.add_argument("--force",
                                 action="store_true",
                                 help="synchronize even if tracker reports a recent sync")
    force_arggroup2.add_argument("--no-force",
                                 action="store_true", dest="no_force",
                                 help="do not synchronize if tracker reports a recent sync (default)")
    dump_arggroup = argparser.add_argument_group("dump control")
    dump_arggroup2 = dump_arggroup.add_mutually_exclusive_group()
    dump_arggroup2.add_argument("--dump",
                                action="store_true",
                                help="enable saving of the megadump to file (default)")
    dump_arggroup2.add_argument("--no-dump",
                                action="store_true", dest="no_dump",
                                help="disable saving of the megadump to file")
    upload_arggroup = argparser.add_argument_group("upload control")
    upload_arggroup2 = upload_arggroup.add_mutually_exclusive_group()
    upload_arggroup2.add_argument("--upload",
                                  action="store_true",
                                  help="upload the dump to the server (default)")
    upload_arggroup2.add_argument("--no-upload",
                                  action="store_true", dest="no_upload",
                                  help="do not upload the dump to the server")
    argparser.add_argument("-I", "--include",
                           nargs="+", metavar="ID",
                           help="list of tracker IDs to sync (all if not specified)")
    argparser.add_argument("-X", "--exclude",
                           nargs="+", metavar="ID",
                           help="list of tracker IDs to not sync")
    cmdlineargs = argparser.parse_args()

    # TODO: Remove this test code
    config = Config()
    print config
    config.logLevel = 'DEBUG'
    config.keepDumps=False
    config.includeTrackers = '123,456,789,abc,DEF'
    config.excludeTrackers = '789,abc,DEF'
    config.dumpDir = "~/.galileo-dump"
    config.doUpload = False
    config.forceSync = True
    print config

    # If an alternative config filename was provided then use it.
    if cmdlineargs.rcconfigname:
        rcconfigname = os.path.expanduser(cmdlineargs.rcconfigname[0])
    else:
        rcconfigname = os.path.expanduser(DEFAULT_RCFILE_NAME)

    # Load the YAML configuration file.
    config = {}
    if os.path.exists(rcconfigname) or cmdlineargs.rcconfigname:
        try:
            logger.debug("Trying to load config file: %s", rcconfigname)
            config = yaml.load(open(rcconfigname, 'rt'))
        except IOError:
            logger.warning('Unable to load configuration file: %s', rcconfigname)
    if config == None:
        config = {}

    # Override rcfile-provided values with those on the command-line.

    # Logging
    if cmdlineargs.verbose:
        config['logging'] = 'verbose'
    elif cmdlineargs.debug:
        config['logging'] = 'debug'
    elif cmdlineargs.silent:
        config['logging'] = 'default'
    if not 'logging' in config:
        config['logging'] = 'default'
    if config['logging'] == 'verbose':
        config['log_level'] = logging.INFO
    elif config['logging'] == 'debug':
        config['log_level'] = logging.DEBUG
    else:
        config['log_level'] = logging.WARNING

    # Includes
    if cmdlineargs.include:
        config['include-trackers'] = cmdlineargs.include
    if not 'include-trackers' in config:
        config['include-trackers'] = None

    # Excludes
    if cmdlineargs.exclude:
        config['exclude-trackers'] = cmdlineargs.exclude
    if not 'exclude-trackers' in config:
        config['exclude-trackers'] = []

    # Keep dumps (or not)
    if cmdlineargs.no_dump:
        config['keep-dumps'] = False
    elif cmdlineargs.dump:
        config['keep-dumps'] = True
    if not 'keep-dumps' in config:
        config['keep-dumps'] = True

    # Dump directory
    if cmdlineargs.dump_dir:
        config['dump-dir'] = cmdlineargs.dump_dir
    if not 'dump-dir' in config:
        config['dump-dir'] = DEFAULT_DUMP_DIR

    # Upload data (or not)
    if cmdlineargs.no_upload:
        config['do-upload'] = False
    elif cmdlineargs.upload:
        config['do-upload'] = True
    if not 'do-upload' in config:
        config['do-upload'] = True

    # Force (or not)
    if cmdlineargs.no_force:
        config['force-sync'] = False
    elif cmdlineargs.force:
        config['force-sync'] = True
    if not 'force-sync' in config:
        config['force-sync'] = False

    logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', level=config['log_level'])

    # Make sure the tracker IDs in the include/exclude lists are all
    # in upper-case to ease comparisons later.
    if config['include-trackers'] is not None:
        config['include-trackers'] = [str(x).upper() for x in config['include-trackers']]
    config['exclude-trackers'] = [str(x).upper() for x in config['exclude-trackers']]

    try:
        total, success, skipped = syncAllTrackers(config)
    except PermissionDeniedException:
        print PERMISSION_DENIED_HELP
        return

    print '%d trackers found, %d skipped, %d successfully synchronized' % (total, skipped, success)

if __name__ == "__main__":
    main()
