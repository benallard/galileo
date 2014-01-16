#!/usr/bin/env python
"""\
galileo.py Utility to synchronize a fitbit tracker with the fitbit server.

Copyright (C) 2013-2014 Benoit Allard
"""

import usb.core

import xml.etree.ElementTree as ET

import requests

import base64

import time
import os

__version__ = '0.2'

def a2x(a, shorten=False):
    shortened = 0
    if shorten:
        while a[-1] == 0:
            shortened += 1
            del a[-1]
    s = ''
    if shortened:
        s = ' 00 (%d times)' % shortened
    return ' '.join('%02X' % x for x in a) + s

def s2x(s):
    return ' '.join('%02X' % ord(c) for c in s)

def a2s(a):
    return ''.join(chr(c) for c in a)

def s2a(s):
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

    def __delete__(self):
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


class NoDongleException(Exception): pass

class TimeoutError(Exception): pass

class FitBitDongle(USBDevice):
    VID = 0x2687
    PID = 0xfb01

    def __init__(self):
        USBDevice.__init__(self, self.VID, self.PID)

    def setup(self):
        if self.dev is None:
            raise NoDongleException()
        if self.dev.is_kernel_driver_active(0):
            self.dev.detach_kernel_driver(0)
        if self.dev.is_kernel_driver_active(1):
            self.dev.detach_kernel_driver(1)
        cfg = self.dev.get_active_configuration();
        self.DataIF = cfg[(0, 0)]
        self.CtrlIF = cfg[(1, 0)]
        
        self.dev.set_configuration()

    def ctrl_write(self, data, timeout=2000):
        print '-->', a2x(data)
        l = self.dev.write(0x02, data, self.CtrlIF.bInterfaceNumber, timeout=timeout)
        if l != len(data):
            print 'Bug, sent %d, had %d' % (l, len(data))

    def ctrl_read(self, timeout=2000, length=32):
        try:
            data = self.dev.read(0x82, length, self.CtrlIF.bInterfaceNumber, timeout=timeout)
        except usb.core.USBError, ue:
            if ue.errno == 110:
                raise TimeoutError
            raise
        if list(data[:2]) == [0x20, 1]:
            print '<--', a2x(data[:2]), a2s(data[2:])
        else:
            print '<--', a2x(data, True)
        return data


    def data_write(self, msg, timeout=2000):
        print '==>', msg
        l = self.dev.write(0x01, msg.asList(), self.DataIF.bInterfaceNumber, timeout=timeout)
        if l != 32:
            print 'Bug, sent %d, had 32' % l

    def data_read(self, timeout=2000):
        try:
            data = self.dev.read(0x81, 32, self.DataIF.bInterfaceNumber, timeout=timeout)
        except usb.core.USBError, ue:
            if ue.errno == 110:
                raise TimeoutError
            raise
        msg = DM(data, out=False)
        print '<==', msg
        return msg


class Tracker(object):
    def __init__(self, Id, addrType, serviceUUID):
        self.id = Id
        self.addrType = addrType
        self.serviceUUID = serviceUUID


class FitbitClient(object):
    def __init__(self, dongle):
        self.dongle = dongle

    def disconnect(self):
        self.dongle.ctrl_write([2, 2])
        self.dongle.ctrl_read() # CancelDiscovery
        self.dongle.ctrl_read() # TerminateLink
        try:
            self.dongle.ctrl_read()
            self.dongle.ctrl_read()
            self.dongle.ctrl_read()
        except TimeoutError:
            # assuming link terminated
            pass

    def getDongleInfo(self):
        self.dongle.ctrl_write([2, 1, 0, 0x78, 1, 0x96])
        d = self.dongle.ctrl_read()
        self.major = d[2]
        self.minor = d[3]
        
    def discover(self):
        self.dongle.ctrl_write([0x1a, 4, 0xba, 0x56, 0x89, 0xa6, 0xfa, 0xbf,
                           0xa2, 0xbd, 1, 0x46, 0x7d, 0x6e, 0, 0,
                           0xab, 0xad, 0, 0xfb, 1, 0xfb, 2, 0xfb,
                           0xa0, 0x0f, 0, 0xd3, 0, 0, 0, 0])
        self.dongle.ctrl_read() # StartDiscovery
        d = self.dongle.ctrl_read(10000)
        while d[0] != 3:
            trackerId = list(d[2:8])
            addrType = list(d[8:9])
            serviceUUID = list(d[17:19])
            yield Tracker(trackerId, addrType, serviceUUID)
            d = self.dongle.ctrl_read(4000)

        # tracker found, cancel discovery
        self.dongle.ctrl_write([2, 5])
        self.dongle.ctrl_read() # CancelDiscovery

    def establishLink(self, tracker):
        self.dongle.ctrl_write([0xb, 6]+tracker.id+tracker.addrType+tracker.serviceUUID)
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

    def getmegaDump(self):
        print 'Megadump'

        # begin Megadump
        self.dongle.data_write(DM([0xc0, 0x10, 0xd]))
        self.dongle.data_read()

        dump = []
        # megadump body
        d = self.dongle.data_read()
        dump.extend(d.data)
        while d.data[0] != 0xc0:
            d = self.dongle.data_read()
            dump.extend(unSLIP1(d.data))
        # megadump footer
        dataType = d.data[2]
        nbBytes = d.data[6] * 0xff + d.data[5]
        transportCRC = d.data[3] * 0xff + d.data[4]
        esc1 = d.data[7]
        esc2 = d.data[8]
        print len(dump), nbBytes
        print 'Done'
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


class SyncError(Exception): pass


class GalileoClient(object):
    ID = '6de4df71-17f9-43ea-9854-67f842021e05'

    def __init__(self, url):
        self.url = url

    def requestStatus(self):
        client = ET.Element('galileo-client')
        client.set('version', '2.0')
        info = ET.SubElement(client, 'client-info')
        id = ET.SubElement(info, 'client-id')
        id.text= self.ID
        version = ET.SubElement(info, 'client-version')
        version.text =  __version__
        mode = ET.SubElement(info, 'client-mode')
        mode.text='status'


        class MyFile(object):
            """ I need a file-like object to write the xml to memory """
            def __init__(self): self.data = ""
            def write(self, data): self.data += data

        tree = ET.ElementTree(client)
        f = MyFile()
        tree.write(f, xml_declaration=True, encoding="UTF-8")

        r = requests.post(self.url,
                          data= f.data,
                          headers={"Content-Type": "text/xml"})
        r.raise_for_status()
        
    def sync(self, major, minor, trackerId, megadump):
        client = ET.Element('galileo-client')
        client.set('version', '2.0')
        info = ET.SubElement(client, 'client-info')
        id = ET.SubElement(info, 'client-id')
        id.text= self.ID
        version = ET.SubElement(info, 'client-version')
        version.text =  __version__
        mode = ET.SubElement(info, 'client-mode')
        mode.text='sync'
        dongle = ET.SubElement(info, 'dongle-version')
        dongle.set('major', str(major))
        dongle.set('minor', str(minor))
        tracker = ET.SubElement(client, 'tracker')
        tracker.set('tracker-id', trackerId)
        data = ET.SubElement(tracker, 'data')
        data.text = base64.b64encode(a2s(megadump))

        class MyFile(object):
            def __init__(self): self.data = ""
            def write(self, data): self.data += data

        tree = ET.ElementTree(client)
        f = MyFile()
        tree.write(f, xml_declaration=True, encoding="UTF-8")

        print f.data
        r = requests.post(self.url,
                          data= f.data,
                          headers={"Content-Type": "text/xml"})
        r.raise_for_status()

        print r.text

        server = ET.fromstring(r.text)
        
        tracker = server.find('tracker')
        if tracker is None:
            raise SyncError('no tracker')
        if tracker.get('tracker-id') != trackerId:
            print 'Got the response for another tracker ... ', tracker.get('tracker-id'), trackerId
        if tracker.get('type') != 'megadumpresponse':
            print 'Not a megadumpresponse ...'

        data = tracker.find('data')

        d = base64.b64decode(data.text)

        return s2a(d)

def main():
    dongle = FitBitDongle()
    dongle.setup()

    fitbit = FitbitClient(dongle)

    galileo = GalileoClient('http://client.fitbit.com/tracker/client/message')

    fitbit.disconnect()

    fitbit.getDongleInfo()

    trackers = [t for t in fitbit.discover()]

    print "%d trackers found" % len(trackers)

    for tracker in trackers:

        try:
            galileo.requestStatus()
        except request.exceptions.ConnectionError:
            # No internet connection or fitbit server down
            print "Not able to connect to the fitbit server."
            print "Check your internet connection"
            return

        try:
            fitbit.establishLink(tracker)
        except TimeoutError:
            # tracker was known, but disapeared in the meantime
            continue

        fitbit.enableTxPipe()

        fitbit.initializeAirlink()

        dump = fitbit.getmegaDump()

        trackerid = ''.join('%02X' % c for c in tracker.id)

        # Write the dump somewhere for archiving ...
        dirname = os.path.expanduser(os.path.join('~', '.galileo', trackerid))
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        filename = os.path.join(dirname, 'dump-%d.txt' % int(time.time()))
        with open(filename, 'wt') as dumpfile:
            for i in range(0, len(dump), 20):
                dumpfile.write(a2x(dump[i:i+20])+'\n')
            
        try:
            response = galileo.sync(fitbit.major, fitbit.minor, 
                                    trackerid, dump)

            with open(filename, 'at') as dumpfile:
                dumpfile.write('\n')
                for i in range(0, len(response), 20):
                    dumpfile.write(a2x(response[i:i+20])+'\n')

            fitbit.uploadResponse(response)
        except SyncError:
            print "Error synchronizing"

        fitbit.disableTxPipe()

        fitbit.terminateAirlink()

    print "Done."

if __name__ == "__main__":
    main()
