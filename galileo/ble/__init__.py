import logging
logger = logging.getLogger(__name__)

from ..dump import Dump, DumpResponse, MEGADUMP
from ..utils import a2x, i2lsba, a2lsbi

class API(object):
    def setup(self):
        raise NotImplementedError
    def disconnectAll(self):
        pass
    def getHardwareInfo(self):
        pass
    def discover(self, UUID):
        raise NotImplementedError
    def connect(self, tracker):
        raise NotImplementedError
    def disconnect(self, tracker):
        raise NotImplementedError
    def _writeData(self, dm):
        raise NotImplementedError
    def _readData(self, timeout=0):
        raise NotImplementedError



    def _initializeAirlink(self, tracker=None):
        """ :returns: a boolean about the successful execution """
        nums = [10, 6, 6, 0, 200]
        #nums = [1, 8, 16, 0, 200]
        #nums = [1034, 6, 6, 0, 200]
        data = []
        for n in nums:
            data.extend(i2lsba(n, 2))
        #data = data + [1]
        self._writeData(DM([0xc0, 0xa] + data))
        d = self._readData()
        if d is None:
            return False
        if d.data[:2] != bytearray([0xc0, 0x14]):
            logger.error("Wrong header: %s", a2x(d.data[:2]))
            return False
        if (tracker is not None) and (d.data[6:12] != tracker._id):
            logger.error("Connected to wrong tracker: %s", a2x(d.data[6:12]))
            return False
        logger.debug("Connection established: %d, %d",
                     a2lsbi(d.data[2:4]), a2lsbi(d.data[4:6]))
        return True

    def displayCode(self):
        """ :returns: a boolean about the successful execution """
        logger.debug('Displaying code on tracker')
        self._writeData(DM([0xc0, 6]))
        r = self._readData()
        return (r is not None) and (r.data == bytearray([0xc0, 2]))

    def getDump(self, dumptype=MEGADUMP):
        """ :returns: a `Dump` object or None """
        logger.debug('Getting dump type %d', dumptype)

        # begin dump of appropriate type
        self._writeData(DM([0xc0, 0x10, dumptype]))
        r = self._readData()
        if r and (r.data[:3] != bytearray([0xc0, 0x41, dumptype])):
            logger.error("Tracker did not acknowledged the dump type: %s", r)
            return None

        dump = Dump(dumptype)
        # Retrieve the dump
        d = self._readData()
        if d is None:
            return None
        dump.add(d.data)
        while d.data[0] != 0xc0:
            d = self._readData()
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
        self._writeData(DM([0xc0, 0x24, dumptype] + i2lsba(len(response), 6)))
        d = self.data_read()
        if d != DM([0xc0, 0x12, dumptype, 0, 0]):
            logger.error("Tracker did not acknowledged upload type: %s", d)
            return False

        CHUNK_LEN = 20
        response = DumpResponse(response, CHUNK_LEN)

        for i, chunk in enumerate(response):#range(0, len(response), CHUNK_LEN):
            self._writeData(DM(chunk))
            # This one can also take some time (Charge HR tracker)
            d = self._readData(20000)
            expected = DM([0xc0, 0x13, (((i+1) % 16) << 4) + dumptype, 0, 0])
            if d != expected:
                logger.error("Wrong sequence number: %s, expected: %s", d, expected)
                return False

        self._writeData(DM([0xc0, 2]))
        # Next one can be very long. He is probably erasing the memory there
        d = self._readData(60000)
        if d != DM([0xc0, 2]):
            logger.error("Unexpected answer from tracker: %s", d)
            return False

        return True



class DataMessage(object):
    """ A message that get communicated over the BLE link """
    LENGTH = 32

    def __init__(self, data, out=True):
        if out:  # outgoing
            if len(data) > (self.LENGTH - 1):
                raise ValueError('data %s (%d) too big' % (data, len(data)))
            self.data = bytearray(data)
            self.len = len(data)
        else:  # incoming
            if len(data) == self.LENGTH:
                # last byte is length
                self.len = data[-1]
                self.data = bytearray(data[:self.len])
            else:
                # Same as outgoing actually
                self.__init__(data)

    def asList(self):
        return self.data + b'\x00' * (self.LENGTH - 1 - self.len) + bytearray([self.len])

    def __eq__(self, other):
        if other is None: return False
        return self.data == other.data

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return ' '.join(['[', a2x(self.data), ']', '-', str(self.len)])

DM = DataMessage
