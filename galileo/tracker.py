from ctypes import c_byte

import logging
logger = logging.getLogger(__name__)

from .dongle import TimeoutError, DM
from .dump import Dump
from .utils import a2x, i2lsba

MICRODUMP = 3
MEGADUMP = 13


class Tracker(object):
    def __init__(self, Id, addrType, attributes, serviceUUID=None):
        self.id = Id
        self.addrType = addrType
        if serviceUUID is None:
            self.serviceUUID = [Id[1] ^ Id[3] ^ Id[5], Id[0] ^ Id[2] ^ Id[4]]
        else:
            self.serviceUUID = serviceUUID
        self.attributes = attributes

    @property
    def syncedRecently(self):
        return self.attributes[1] != 4


class FitbitClient(object):
    def __init__(self, dongle):
        self.dongle = dongle

    def disconnect(self):
        logger.info('Disconnecting from any connected trackers')

        self.dongle.ctrl_write([2, 2])
        self.dongle.ctrl_read()  # CancelDiscovery
        self.dongle.ctrl_read()  # TerminateLink

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
            logger.debug('Fitbit dongle version major:%d minor:%d', self.major,
                         self.minor)
        except TimeoutError:
            logger.error('Failed to get connected Fitbit dongle information')
            raise

    def discover(self, uuid, service1=0xfb00, write=0xfb01, read=0xfb02,
                 minDuration=4000):
        """\
        The uuid is a mask on the service (characteristics ?) we understand
        service1 parameter is unused (at lease for the 'One')
        read and write are the uuid of the characteristics we use for
        transmission and reception.
        """
        logger.debug('Discovering for UUID %s: %s', uuid,
             ', '.join(hex(s) for s in (service1, write, read)))
        cmd = [0x1a, 4]
        cmd += i2lsba(uuid.int, 16)
        for i in (service1, write, read, minDuration):
            cmd += i2lsba(i, 2)
        self.dongle.ctrl_write(cmd)
        d = self.dongle.ctrl_read()  # StartDiscovery
        # Sometimes, the dongle immediately answers 'no trackers'
        # (that's a mistake from our side)
        if list(d[:3]) == [3, 2, 0]:
            self.dongle.ctrl_read()
            logger.critical('Discovery went wrong')
        else:
            d = self.dongle.ctrl_read(minDuration)
        while d[0] != 3:
            trackerId = list(d[2:8])
            addrType = d[8]
            RSSI = c_byte(d[9]).value
            attributes = list(d[11:13])
            sUUID = list(d[17:19])
            serviceUUID = [trackerId[1] ^ trackerId[3] ^ trackerId[5],
                           trackerId[0] ^ trackerId[2] ^ trackerId[4]]
            tracker = Tracker(trackerId, addrType, attributes, sUUID)
            if not tracker.syncedRecently and (serviceUUID != sUUID):
                logger.error("Error in communication to tracker %s, cannot acknowledge the serviceUUID: %s vs %s",
                             a2x(trackerId, delim=""), a2x(serviceUUID, ':'), a2x(sUUID, ':'))
            logger.debug('Tracker: %s, %s, %s, %s', a2x(trackerId, ':'), addrType, RSSI, a2x(attributes, ':'))
            if RSSI < -80:
                logger.info("Tracker %s has low signal power (%ddBm), higher"
                            " chance of miscommunication",
                            a2x(trackerId, delim=""), RSSI)
            if not tracker.syncedRecently:
                logger.debug('Tracker %s was not recently synchronized', a2x(trackerId, delim=""))
            yield tracker
            d = self.dongle.ctrl_read(minDuration)

        # tracker found, cancel discovery
        self.dongle.ctrl_write([2, 5])
        self.dongle.ctrl_read()  # CancelDiscovery

    def establishLink(self, tracker):
        self.dongle.ctrl_write([0xb, 6] + tracker.id + [tracker.addrType] + tracker.serviceUUID)
        self.dongle.ctrl_read()  # EstablishLink
        self.dongle.ctrl_read(5000)
        # established, waiting for service discovery
        # - This one takes long
        self.dongle.ctrl_read(8000)  # GAP_LINK_ESTABLISHED_EVENT
        self.dongle.ctrl_read()

    def toggleTxPipe(self, on):
        """ `on` is a boolean that dictate the status of the pipe """
        byte = 0
        if on:
            byte = 1
        self.dongle.ctrl_write([3, 8, byte])
        d = self.dongle.data_read(5000)
        return d.data == [0xc0, 0xb]

    def initializeAirlink(self):
        data = [0xa, 0, 6, 0, 6, 0, 0, 0, 0xc8, 0]
        #data = [1, 0, 8, 0, 0x10, 0, 0, 0, 0xc8, 0, 1]
        self.dongle.data_write(DM([0xc0, 0xa] + data))
        self.dongle.ctrl_read(10000)
        self.dongle.data_read()

    def getDump(self, dumptype=MEGADUMP):
        logger.debug('Getting dump type %d', dumptype)

        # begin dump of appropriate type
        self.dongle.data_write(DM([0xc0, 0x10, dumptype]))
        r = self.dongle.data_read()
        assert r.data == [0xc0, 0x41, dumptype], r.data

        dump = Dump(dumptype)
        # Retrieve the dump
        d = self.dongle.data_read()
        dump.add(d.data)
        while d.data[0] != 0xc0:
            d = self.dongle.data_read()
            dump.add(d.data)
        # Analyse the dump
        if not dump.isValid():
            logger.error('Dump not valid')
        logger.debug('Dump done, length %d, transportCRC=0x%04x, esc1=0x%02x, esc2=0x%02x', dump.len, dump.crc.final(), dump.esc[0], dump.esc[1])
        return dump

    def uploadResponse(self, response):
        self.dongle.data_write(DM([0xc0, 0x24, 4] + i2lsba(len(response), 6)))
        self.dongle.data_read()

        for i in range(0, len(response), 20):
            self.dongle.data_write(DM(response[i:i + 20]))
            self.dongle.data_read()

        self.dongle.data_write(DM([0xc0, 2]))
        self.dongle.data_read(60000)  # This one can be very long. He is probably erasing the memory there
        self.dongle.data_write(DM([0xc0, 1]))
        self.dongle.data_read()

    def terminateAirlink(self):
        self.dongle.ctrl_write([2, 7])
        self.dongle.ctrl_read()  # TerminateLink

        self.dongle.ctrl_read()
        self.dongle.ctrl_read()  # GAP_LINK_TERMINATED_EVENT
        self.dongle.ctrl_read()  # 22
