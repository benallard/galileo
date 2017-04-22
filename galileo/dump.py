import base64
import logging

logger = logging.getLogger(__name__)

from .utils import a2x, a2lsbi, a2b

MICRODUMP = 3
MEGADUMP = 13


class CRC16(object):
    """ A rather generic CRC16 class """
    def __init__(self, poly=0x1021, Invert=True, IV=0x0000, FV=0x0000):
        self.poly = poly
        self.value = IV
        self.FV = FV
        if Invert:
            self.update_byte = self.update_byte_MSB
        else:
            self.update_byte = self.update_byte_LSB

    def update_byte_MSB(self, byte):
        self.value ^= byte << 8
        for i in range(8):
            if self.value & 0x8000:
                self.value = (self.value << 1) ^ self.poly
            else:
                self.value <<= 1
        self.value &= 0xffff

    def update_byte_LSB(self, byte):
        self.value ^= byte
        for i in range(8):
            if self.value & 0x0001:
                self.value = (self.value >> 1) ^ self.poly
            else:
                self.value >>= 1

    def update(self, array):
        for c in array:
            self.update_byte(c)

    def final(self):
        return self.value ^ self.FV


class TrackerBlock(object):
    def __init__(self):
        self.data = bytearray()
        self.footer = bytearray()

    @property
    def len(self):
        return len(self.data)


    @property
    def megadumpType(self):
        if self.len < 1:
            return None
        return a2x(self.data[0:1])

    @property
    def encryption(self):
        if self.len < 6:
            return None
        return a2lsbi(self.data[4:6])

    @property
    def nonce(self):
        if self.len < 10:
            return None
        return self.data[6:10]

    def toFile(self, filename):
        logger.debug("Dumping megadump to %s", filename)
        with open(filename, 'wt') as dumpfile:
            for i in range(0, self.len, 20):
                dumpfile.write(a2x(self.data[i:i + 20]) + '\n')
            dumpfile.write(a2x(self.footer) + '\n')


class Dump(TrackerBlock):
    def __init__(self, _type):
        TrackerBlock.__init__(self)
        self._type = _type
        self.crc = CRC16()
        self.esc = [0, 0]

    @property
    def serial(self):
        if self.len < 16:
            return None
        return a2x(self.data[10:16], delim='')

    @property
    def trackerType(self):
        if self.len < 16:
            return None
        return a2lsbi(self.data[15:16])

    def unSLIP1(self, data):
        """ The protocol uses a particular version of SLIP (RFC 1055) applied
        only on the first byte of the data"""
        END = 0xC0
        ESC = 0xDB
        ESC_ = {0xDC: END,
                0xDD: ESC}
        if data[0] == ESC:
            # increment the escape counter
            self.esc[data[1] - 0xDC] += 1
            # return the escaped value
            return bytearray([ESC_[data[1]]]) + data[2:]
        return data

    def add(self, data):
        if data[0] == 0xc0:
            assert len(self.footer) == 0
            self.footer = bytearray(data)
            return
        data = self.unSLIP1(data)
        self.crc.update(data)
        self.data.extend(data)

    def isValid(self):
        if not self.footer:
            return False
        ret = True
        dataType = self.footer[2]
        if dataType != self._type:
            logger.error('Dump is not of requested type: %x != %x',
                         dataType, self._type)
            ret = False
        nbBytes = a2lsbi(self.footer[5:9])
        if self.len != nbBytes:
            logger.error("Error in communication, Expected length: %d bytes,"
                         " received %d bytes", nbBytes, self.len)
            ret = False
        crcVal = self.crc.final()
        transportCRC = a2lsbi(self.footer[3:5])
        if transportCRC != crcVal:
            logger.error("Error in communication, Expected CRC: 0x%04X,"
                         " received 0x%04X", crcVal, transportCRC)
            ret = False
        return ret

    def toBase64(self):
        return base64.b64encode(a2b(self.data + self.footer)).decode('utf-8')


class DumpResponse(TrackerBlock):
    def __init__(self, data, chunk_len):
        TrackerBlock.__init__(self)
        self.data = bytearray(data)
        self._chunk_len = chunk_len
        self.__index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.__index >= len(self.data):
            raise StopIteration
        if self.data[self.__index] not in (0xC0, 0xDB):
            self.__index += self._chunk_len
            return self.data[self.__index-self._chunk_len:self.__index]
        b = self.data[self.__index]
        self.__index += self._chunk_len - 1
        return bytearray([0xDB, {0xC0: 0xDC, 0xDB: 0xDD}[b]]) + self.data[self.__index-self._chunk_len+2:self.__index]
    # For python2
    next = __next__
