from ctypes import c_byte

import logging
logger = logging.getLogger(__name__)

from . import ble
from . import dongle
from .dongle import CM, DM, isStatus
from .dump import Dump, DumpResponse, MEGADUMP
from .utils import a2s, a2x, i2lsba, a2lsbi


class Tracker(object):
    def __init__(self, Id, addrType, serviceData, RSSI, serviceUUID=None):
        self.id = Id
        self.addrType = addrType
        if serviceUUID is None:
            self.serviceUUID = a2lsbi([Id[1] ^ Id[3] ^ Id[5],
                                       Id[0] ^ Id[2] ^ Id[4]])
        else:
            self.serviceUUID = serviceUUID
        self.serviceData = serviceData
        # following three are coded somewhere here ...
        # specialMode
        # canDisplayNumber
        # colorCode
        self.RSSI = RSSI
        self.status = 'unknown'  # If we happen to read it before anyone set it

    @property
    def productId(self):
        return self.serviceData[0]

    @property
    def syncedRecently(self):
        return self.serviceData[1] != 4

    @classmethod
    def fromDiscovery(klass, data, minRSSI=-255):
        trackerId = bytearray(data[:6])
        addrType = data[6]
        RSSI = c_byte(data[7]).value
        serviceDataLen = data[8]
        serviceData = data[9:9+serviceDataLen+1]  # '+1': go figure !
        sUUID = a2lsbi(data[15:17])
        serviceUUID = a2lsbi([trackerId[1] ^ trackerId[3] ^ trackerId[5],
                              trackerId[0] ^ trackerId[2] ^ trackerId[4]])
        tracker = klass(trackerId, addrType, serviceData, RSSI, sUUID)
        if not tracker.syncedRecently and (serviceUUID != sUUID):
            logger.debug("Cannot acknowledge the serviceUUID: %s vs %s",
                         a2x(i2lsba(serviceUUID, 2), ':'), a2x(i2lsba(sUUID, 2), ':'))
        logger.debug('Tracker: %s, %s, %s, %s', a2x(trackerId, ':'),
                     addrType, RSSI, a2x(serviceData, ':'))
        if RSSI < -80:
            logger.info("Tracker %s has low signal power (%ddBm), higher"
                        " chance of miscommunication",
                        a2x(trackerId, delim=""), RSSI)

        if not tracker.syncedRecently:
            logger.debug('Tracker %s was not recently synchronized',
                         a2x(trackerId, delim=""))
        if RSSI < minRSSI:
            logger.warning("Tracker %s below power threshold (%ddBm),"
                           "dropping", a2x(trackerId, delim=""), minRSSI)
            #continue
        return tracker

    def getID(self):
        return a2x(self.id, delim="")


class FitbitClient(dongle.FitBitDongle, ble.API):
    def disconnect(self):
        logger.info('Disconnecting from any connected trackers')

        self.ctrl_write(CM(2))
        if not isStatus(self.ctrl_read(), 'CancelDiscovery'):
            return False
        # Next one is not critical. It can happen that it does not comes
        isStatus(self.ctrl_read(), 'TerminateLink')

        self.exhaust()

        return True

    def exhaust(self):
        """ We exhaust the pipe, then we know that we have a clean state """
        logger.debug("Exhausting the communication pipe")
        goOn = True
        while goOn:
            goOn = self.ctrl_read() is not None

    def getDongleInfo(self):
        self.ctrl_write(CM(1))
        d = self.ctrl_read()
        if (d is None) or (d.INS != 8):
            return False
        self.setVersion(d.payload[0], d.payload[1])
        self.address = d.payload[2:8]
        self.flashEraseTime = a2lsbi(d.payload[8:10])
        self.firmwareStartAddress = a2lsbi(d.payload[10:14])
        self.firmwareEndAddress = a2lsbi(d.payload[14:18])
        self.ccIC = d.payload[18]
        # Not sure how the last ones fit in the last byte
#        self.hardwareRevision = d.payload[19]
#        self.revision = d.payload[19]
        return True

    def discover(self, uuid, service1=0xfb00, write=0xfb01, read=0xfb02,
                 minRSSI=-255, minDuration=4000):
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
        self.ctrl_write(CM(4, data))
        amount = 0
        while True:
            # Give the dongle 100ms margin
            d = self.ctrl_read(minDuration + 100)
            if d is None: break
            elif isStatus(d, None, False):
                # We know this can happen almost any time during 'discovery'
                logger.info('Ignoring message: %s' % a2s(d.payload))
                continue
            elif d.INS == 2:
                # Last instruction of a discovery sequence has INS==1
                break
            elif (d.INS != 3) or (len(d.payload) < 17):
                logger.error('payload unexpected: %s', d)
                break
            yield Tracker.fromDiscovery(d.payload, minRSSI)
            amount += 1

        if d != CM(2, [amount]):
            logger.error('%d trackers discovered, dongle says %s', amount, d)
        # tracker found, cancel discovery
        self.ctrl_write(CM(5))
        d = self.ctrl_read()
        if isStatus(d, 'StartDiscovery', False):
            # We had not received the 'StartDiscovery' yet
            d = self.ctrl_read()
        isStatus(d, 'CancelDiscovery')

    def setPowerLevel(self, level):
        # This is quite weird as in the log I took this from, they send:
        # 020D05 (level5), but as the length is 02, I believe the 05 is not
        # even acknowledged by the dongle ...
        self.ctrl_write(CM(0xd, [level]))
        r = self.ctrl_read()
        if r != CM(0xFE):
            return False
        return True

    def establishLink(self, tracker):
        if self.useEstablishLinkEx:
            return self.establishLinkEx(tracker)
        self.ctrl_write(CM(6, tracker.id + bytearray([tracker.addrType] +
                                  i2lsba(tracker.serviceUUID, 2))))
        d = self.ctrl_read()
        if d == CM(0xff, [2, 3]):
            # Our detection based on the dongle version is not perfect :(
            logger.warning("Older tracker %d.%d also needs EstablishLinkEx",
                           self.major, self.minor)
            self.useEstablishLinkEx = True
            return self.establishLinkEx(tracker)
        elif not isStatus(d, 'EstablishLink'):
            return False
        d = self.ctrl_read(5000)
        if d != CM(4, [0]):
            logger.error('Unexpected message: %s', d)
            return False
        # established, waiting for service discovery
        # - This one takes long
        if not isStatus(self.ctrl_read(8000),
                        'GAP_LINK_ESTABLISHED_EVENT'):
            return False
        # This one can also take some time (Charge tracker)
        d = self.ctrl_read(5000)
        if d != CM(7):
            logger.error('Unexpected 2nd message: %s', d)
            return False
        return True

    def establishLinkEx(self, tracker):
        """ First heard from in #236 """
        self.ctrl_write(CM(0x19, [1, 0]))
        nums = [6, 6, 0, 200]  # Looks familiar ?
        data = tracker.id + bytearray([tracker.addrType])
        for n in nums:
            data.extend(i2lsba(n, 2))
        self.ctrl_write(CM(0x12, data))
        if not isStatus(self.ctrl_read(), 'EstablishLinkEx'):
            return False
        d = self.ctrl_read(5000)
        if d != CM(4, [0]):
            logger.error('Unexpected message: %s', d)
            return False
        if not isStatus(self.ctrl_read(),
                        'GAP_LINK_ESTABLISHED_EVENT'):
            return False
        d = self.ctrl_read()
        if d.INS == 6:
            d = self.ctrl_read()
        if d != CM(7):
            logger.error('Unexpected 2nd message: %s', d)
            return False
        return True

    def toggleTxPipe(self, on):
        """ `on` is a boolean that dictate the status of the pipe
        :returns: a boolean about the successful execution
        """
        self.ctrl_write(CM(8, [int(on)]))
        d = self.data_read(5000)
        return d == DM([0xc0, 0xb])

    def initializeAirlink(self, tracker=None):
        """ :returns: a boolean about the successful execution """
        nums = [10, 6, 6, 0, 200]
        #nums = [1, 8, 16, 0, 200]
        #nums = [1034, 6, 6, 0, 200]
        data = []
        for n in nums:
            data.extend(i2lsba(n, 2))
        #data = data + [1]
        self.data_write(DM([0xc0, 0xa] + data))
        if not self.useEstablishLinkEx:
            # Not necessary when using establishLinkEx
            d = self.ctrl_read(10000)
            if d != CM(6, data[-6:]):
                logger.error("Unexpected message: %s != %s", d, CM(6, data[-6:]))
                return False
        d = self.data_read()
        if d is None:
            return False
        if d.data[:2] != bytearray([0xc0, 0x14]):
            logger.error("Wrong header: %s", a2x(d.data[:2]))
            return False
        if (tracker is not None) and (d.data[6:12] != tracker.id):
            logger.error("Connected to wrong tracker: %s", a2x(d.data[6:12]))
            return False
        logger.debug("Connection established: %d, %d",
                     a2lsbi(d.data[2:4]), a2lsbi(d.data[4:6]))
        return True

    def displayCode(self):
        """ :returns: a boolean about the successful execution """
        logger.debug('Displaying code on tracker')
        self.data_write(DM([0xc0, 6]))
        r = self.data_read()
        return (r is not None) and (r.data == bytearray([0xc0, 2]))

    def getDump(self, dumptype=MEGADUMP):
        """ :returns: a `Dump` object or None """
        logger.debug('Getting dump type %d', dumptype)

        # begin dump of appropriate type
        self.data_write(DM([0xc0, 0x10, dumptype]))
        r = self.data_read()
        if r and (r.data[:3] != bytearray([0xc0, 0x41, dumptype])):
            logger.error("Tracker did not acknowledged the dump type: %s", r)
            return None

        dump = Dump(dumptype)
        # Retrieve the dump
        d = self.data_read()
        if d is None:
            return None
        dump.add(d.data)
        while d.data[0] != 0xc0:
            d = self.data_read()
            if d is None:
                return None
            dump.add(d.data)
        # Analyse the dump
        if not dump.isValid():
            logger.error('Dump not valid')
            return None
        logger.debug("Dump done, length %d, transportCRC=0x%04x, esc1=0x%02x,"
                     " esc2=0x%02x", dump.len, dump.crc.final(), dump.esc[0],
                     dump.esc[1])
        return dump

    def uploadResponse(self, response):
        """ 4 and 6 are magic values here ...
        :returns: a boolean about the success of the operation.
        """
        dumptype = 4  # ???
        self.data_write(DM([0xc0, 0x24, dumptype] + i2lsba(len(response), 6)))
        d = self.data_read()
        if d != DM([0xc0, 0x12, dumptype, 0, 0]):
            logger.error("Tracker did not acknowledged upload type: %s", d)
            return False

        CHUNK_LEN = 20
        response = DumpResponse(response, CHUNK_LEN)

        for i, chunk in enumerate(response):#range(0, len(response), CHUNK_LEN):
            self.data_write(DM(chunk))
            # This one can also take some time (Charge HR tracker)
            d = self.data_read(20000)
            expected = DM([0xc0, 0x13, (((i+1) % 16) << 4) + dumptype, 0, 0])
            if d != expected:
                logger.error("Wrong sequence number: %s, expected: %s", d, expected)
                return False

        self.data_write(DM([0xc0, 2]))
        # Next one can be very long. He is probably erasing the memory there
        d = self.data_read(60000)
        if d != DM([0xc0, 2]):
            logger.error("Unexpected answer from tracker: %s", d)
            return False

        return True

    def terminateAirlink(self):
        """ contrary to ``initializeAirlink`` """

        self.data_write(DM([0xc0, 1]))
        d = self.data_read()
        if d != DM([0xc0, 1]):
            return False
        return True

    def ceaseLink(self):
        """ contrary to ``establishLink`` """

        self.ctrl_write(CM(7))
        d = self.ctrl_read(5000)
        if d is None:
            return False
        if d.INS == 6:
            # that is pretty bad because actually that message was sent long ago
            d = self.ctrl_read()
        if not isStatus(d, 'TerminateLink'):
            return False

        d = self.ctrl_read(3000)
        if (d is None) or (d.INS != 5):
            # Payload can be either 0x16 or 0x08
            return False
        if not isStatus(self.ctrl_read(), 'GAP_LINK_TERMINATED_EVENT'):
            return False
        if not isStatus(self.ctrl_read()):
            # This one doesn't always return '22'
            return False
        return True
