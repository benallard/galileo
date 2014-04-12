from ctypes import c_byte

import logging
logger = logging.getLogger(__name__)

from .dongle import TimeoutError, CM, DM, isStatus
from .dump import Dump
from .utils import a2x, i2lsba, a2lsbi

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
        self.status = 'unknown'  # If we happen to read it before anyone set it

    @property
    def syncedRecently(self):
        return self.attributes[1] != 4


class FitbitClient(object):
    def __init__(self, dongle):
        self.dongle = dongle
        self.hasInfo = False

    def disconnect(self):
        logger.info('Disconnecting from any connected trackers')

        self.dongle.ctrl_write(CM(2))
        if not isStatus(self.dongle.ctrl_read(), 'CancelDiscovery'):
            return False

        try:
            isStatus(self.dongle.ctrl_read(), 'TerminateLink')
            # It is OK to have a timeout with the following ctrl_read as
            # they are there to clean up any connection left open from
            # the previous attempts.
            self.dongle.ctrl_read()
            self.dongle.ctrl_read()
            self.dongle.ctrl_read()
        except TimeoutError:
            # assuming link terminated
            pass

        return True

    def getDongleInfo(self):
        try:
            self.dongle.ctrl_write(CM(1))
            d = self.dongle.ctrl_read()
            self.major = d.payload[0]
            self.minor = d.payload[1]
            logger.debug('Fitbit dongle version major:%d minor:%d', self.major,
                         self.minor)
        except TimeoutError:
            logger.warning('Failed to get connected Fitbit dongle information')
        self.hasInfo = True

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
        data = i2lsba(uuid.int, 16)
        for i in (service1, write, read, minDuration):
            data += i2lsba(i, 2)
        self.dongle.ctrl_write(CM(4, data))
        amount = 0
        while True:
            d = self.dongle.ctrl_read(minDuration)
            if isStatus(d, 'StartDiscovery', False): continue
            elif d.INS == 2: break
            trackerId = d.payload[:6]
            addrType = d.payload[6]
            RSSI = c_byte(d.payload[7]).value
            attributes = d.payload[9:11]
            sUUID = d.payload[15:17]
            serviceUUID = [trackerId[1] ^ trackerId[3] ^ trackerId[5],
                           trackerId[0] ^ trackerId[2] ^ trackerId[4]]
            tracker = Tracker(trackerId, addrType, attributes, sUUID)
            if not tracker.syncedRecently and (serviceUUID != sUUID):
                logger.debug("Cannot acknowledge the serviceUUID: %s vs %s",
                             a2x(serviceUUID, ':'), a2x(sUUID, ':'))
            logger.debug('Tracker: %s, %s, %s, %s', a2x(trackerId, ':'),
                         addrType, RSSI, a2x(attributes, ':'))
            if RSSI < -80:
                logger.info("Tracker %s has low signal power (%ddBm), higher"
                            " chance of miscommunication",
                            a2x(trackerId, delim=""), RSSI)
            if not tracker.syncedRecently:
                logger.debug('Tracker %s was not recently synchronized',
                             a2x(trackerId, delim=""))
            amount += 1
            yield tracker

        if amount != d.payload[0]:
            logger.error('%d trackers discovered, dongle says %d', amount,
                         d.payload[0])
        # tracker found, cancel discovery
        self.dongle.ctrl_write(CM(5))
        d = self.dongle.ctrl_read()
        if isStatus(d, 'StartDiscovery', False):
            # We had not received the 'StartDiscovery' yet
            d = self.dongle.ctrl_read()
        isStatus(d, 'CancelDiscovery')

    def establishLink(self, tracker):
        self.dongle.ctrl_write(CM(6, tracker.id + [tracker.addrType] +
                                  tracker.serviceUUID))
        if not isStatus(self.dongle.ctrl_read(), 'EstablishLink'):
            return False
        if self.dongle.ctrl_read(5000).INS != 4:
            return False
        # established, waiting for service discovery
        # - This one takes long
        if not isStatus(self.dongle.ctrl_read(8000),
                        'GAP_LINK_ESTABLISHED_EVENT'):
            return False
        if self.dongle.ctrl_read().INS != 7:
            return False
        return True

    def toggleTxPipe(self, on):
        """ `on` is a boolean that dictate the status of the pipe """
        byte = 0
        if on:
            byte = 1
        self.dongle.ctrl_write(CM(8, [byte]))
        d = self.dongle.data_read(5000)
        return d.data == [0xc0, 0xb]

    def initializeAirlink(self):
        nums = [0xa, 6, 6, 0, 200]
        #nums = [1, 8, 16, 0, 200]
        data = []
        for n in nums:
            data.extend(i2lsba(n, 2))
        #data = data + [1]
        self.dongle.data_write(DM([0xc0, 0xa] + data))
        d = self.dongle.ctrl_read(10000)
        if d.INS != 6:
            return False
        if [a2lsbi(d.payload[0:2]), a2lsbi(d.payload[2:4]),
                a2lsbi(d.payload[4:6])] != nums[-3:]:
            return False
        self.dongle.data_read()
        return True

    def displayCode(self):
        logger.debug('Displaying code on tracker')
        self.dongle.data_write(DM([0xc0, 6]))
        r = self.dongle.data_read()
        return r.data == [0xc0, 2]

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
        logger.debug("Dump done, length %d, transportCRC=0x%04x, esc1=0x%02x,"
                     " esc2=0x%02x", dump.len, dump.crc.final(), dump.esc[0],
                     dump.esc[1])
        return dump

    def uploadResponse(self, response):
        self.dongle.data_write(DM([0xc0, 0x24, 4] + i2lsba(len(response), 6)))
        self.dongle.data_read()

        for i in range(0, len(response), 20):
            self.dongle.data_write(DM(response[i:i + 20]))
            self.dongle.data_read()

        self.dongle.data_write(DM([0xc0, 2]))
        # Next one can be very long. He is probably erasing the memory there
        self.dongle.data_read(60000)
        self.dongle.data_write(DM([0xc0, 1]))
        self.dongle.data_read()

    def terminateAirlink(self):
        self.dongle.ctrl_write(CM(7))
        if not isStatus(self.dongle.ctrl_read(), 'TerminateLink'):
            return False

        if self.dongle.ctrl_read().INS != 5:
            # Payload can be either 0x16 or 0x08
            return False
        if not isStatus(self.dongle.ctrl_read(), 'GAP_LINK_TERMINATED_EVENT'):
            return False
        if not isStatus(self.dongle.ctrl_read()):
            # This one doesn't always return '22'
            return False
        return True
