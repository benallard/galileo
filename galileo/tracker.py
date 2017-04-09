from ctypes import c_byte

import logging
logger = logging.getLogger(__name__)

from . import ble
from . import dongle
from .ble import DM
from .dongle import CM, isStatus
from .utils import a2s, a2x, i2lsba, a2lsbi

class Tracker(object):
    def __init__(self, id):
        self._id = id
        self.status = 'unknown'  # If we happen to read it before anyone set it

    @property
    def id(self):
        return a2x(self._id, delim="")

    @property
    def syncedRecently(self):
        return False

class FBTracker(Tracker):
    """ The tracker that get used by the Fitbit dongle implementation """
    def __init__(self, Id, addrType, serviceData, RSSI, serviceUUID=None):
        Tracker.__init__(self, Id)
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


class FitbitClient(dongle.FitBitDongle, ble.API):
    def disconnectAll(self):
        logger.info('Disconnecting from any connected trackers')

        self.ctrl_write(CM(2))
        if not isStatus(self.ctrl_read(), 'CancelDiscovery'):
            self._exhaust()
            return False
        # Next one is not critical. It can happen that it does not comes
        isStatus(self.ctrl_read(), 'TerminateLink')

        self._exhaust()

        return True

    def _exhaust(self):
        """ We exhaust the pipe, then we know that we have a clean state """
        logger.debug("Exhausting the communication pipe")
        goOn = True
        while goOn:
            goOn = self.ctrl_read() is not None

    def getHardwareInfo(self):
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

    def discover(self, uuid, service1, read, write, minRSSI, timeout):
        """\
        The uuid is a mask on the service (characteristics ?) we understand
        service1 parameter is unused (at lease for the 'One')
        read and write are the uuid of the characteristics we use for
        transmission and reception.
        """
        logger.debug('Discovering for UUID %s: %s', uuid,
                     ', '.join(hex(s) for s in (service1, write, read)))
        data = i2lsba(uuid.int, 16)
        for i in (service1, write, read, timeout):
            data += i2lsba(i, 2)
        self.ctrl_write(CM(4, data))
        amount = 0
        while True:
            # Give the dongle 100ms margin
            d = self.ctrl_read(timeout + 100)
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
            yield FBTracker.fromDiscovery(d.payload, minRSSI)
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

    def connect(self, tracker):
        if not self._establishLink(tracker):
            logger.error("establishLink failed")
            return False

        if not self._toggleTxPipe(True):
            logger.error("Unable to toggle the TX pipe on")
            return False

        if not self._initializeAirlink(tracker):
            return False

        if not self.useEstablishLinkEx:
            # Not necessary when using establishLinkEx
            d = self.ctrl_read(10000)
            #if d != CM(6, data[-6:]):
            #    logger.error("Unexpected message: %s != %s", d, CM(6, data[-6:]))
            #    return False

        return True

    def _establishLink(self, tracker):
        if self.useEstablishLinkEx:
            return self._establishLinkEx(tracker)
        self.ctrl_write(CM(6, tracker._id + bytearray([tracker.addrType] +
                                  i2lsba(tracker.serviceUUID, 2))))
        d = self.ctrl_read()
        if d == CM(0xff, [2, 3]):
            # Our detection based on the dongle version is not perfect :(
            logger.warning("Older tracker %d.%d also needs EstablishLinkEx",
                           self.major, self.minor)
            self.useEstablishLinkEx = True
            return self._establishLinkEx(tracker)
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

    def _establishLinkEx(self, tracker):
        """ First heard from in #236 """
        self.ctrl_write(CM(0x19, [1, 0]))
        nums = [6, 6, 0, 200]  # Looks familiar ?
        data = tracker._id + bytearray([tracker.addrType])
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
        if d is None:
            return False
        elif d.INS == 6:
            d = self.ctrl_read()
        if d != CM(7):
            logger.error('Unexpected 2nd message: %s', d)
            return False
        return True

    def _toggleTxPipe(self, on):
        """ `on` is a boolean that dictate the status of the pipe
        :returns: a boolean about the successful execution
        """
        self.ctrl_write(CM(8, [int(on)]))
        d = self.data_read(5000)
        return d == DM([0xc0, 0xb])

    def disconnect(self, tracker):
        if not self._terminateAirlink():
            logger.error("Unable to terminate the link")
            return False

        if not self._toggleTxPipe(False):
            logger.error("Unable to close the TX pipe")
            return False

        return self._ceaseLink()

    def _terminateAirlink(self):
        """ contrary to ``initializeAirlink`` """

        self.data_write(DM([0xc0, 1]))
        d = self.data_read()
        if d != DM([0xc0, 1]):
            return False
        return True

    def _ceaseLink(self):
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
