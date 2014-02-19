import base64

import logging
logger = logging.getLogger(__name__)

from .utils import a2x, a2lsbi, a2s

class CRC(object):
    """ An abstract mother class to group the different CRC16 implementations
    """
    def __init__(self, IV, FV=0x0000):
        self.value = IV
        self.FV = FV

    def update(self, array):
        for c in array:
            self.update_byte(c)

    def final(self):
        return self.value ^ self.FV


# Remarks: the following class is not used in the project, however, it
# caries hours of trial and errors trying to figure out the CRC used
# that at the moment, I don't feel like removing it ...
class CRC_CCITT(CRC):
    """ An implementation of the CCITT CRC16 flavor algorithm, taken from
    the linux kernel """
    TABLE = [
        0x0000, 0x1081, 0x2102, 0x3183,
        0x4204, 0x5285, 0x6306, 0x7387,
        0x8408, 0x9489, 0xa50a, 0xb58b,
        0xc60c, 0xd68d, 0xe70e, 0xf78f]

    def __init__(self, IV=0xffff):
        CRC.__init__(self, IV)

    def update_byte(self, byte):
        reg = self.value
        reg = (reg >> 4) ^ CRC_CCITT.TABLE[(reg ^ byte) & 0x000f]
        reg = (reg >> 4) ^ CRC_CCITT.TABLE[(reg ^ (byte >> 4)) & 0x000f]
        self.value = reg


class CRC16(CRC):
    """ A rather generic CRC16 class """
    def __init__(self, poly=0x1021, Invert=True, IV=0x0000, FV=0x0000):
        self.poly = poly
        CRC.__init__(self, IV, FV)
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

class Dump(object):
    def __init__(self, _type):
        self._type = _type
        self.data = []
        self.footer = []
        self.crc = CRC16()
        self.esc = [0, 0]

    def unSLIP1(self, data):
        """ The protocol uses a particular version of SLIP (RFC 1055) applied
        only on the first byte of the data"""
        END = 0300
        ESC = 0333
        ESC_ = {0334: END,
                0335: ESC}
        if data[0] == ESC:
            # increment the escape counter
            self.esc[data[1] - 0334] += 1
            # return the escaped value
            return [ESC_[data[1]]] + data[2:]
        return data

    def add(self, data):
        if data[0] == 0xc0:
            assert self.footer == []
            self.footer = data
            return
        data = self.unSLIP1(data)
        self.crc.update(data)
        self.data.extend(data)

    @property
    def len(self):
        return len(self.data)

    def isValid(self):
        dataType = self.footer[2]
        if dataType != self._type:
            logger.error('Dump is not of requested type: %x != %x',
                         dataType, self._type)
            return False
        nbBytes = a2lsbi(self.footer[5:7])
        transportCRC = a2lsbi(self.footer[3:5])
        if self.len != nbBytes:
            logger.error("Error in communication, Expected length: %d bytes,"
                         " received %d bytes", nbBytes, self.len)
            return False
        crcVal = self.crc.final()
        if transportCRC != crcVal:
            logger.error("Error in communication, Expected CRC: 0x%04X,"
                         " received 0x%04X", crcVal, transportCRC)
            return False
        return True

    def toFile(self, filename):
        logger.debug("Dumping megadump to %s", filename)
        with open(filename, 'wt') as dumpfile:
            for i in range(0, self.len, 20):
                dumpfile.write(a2x(self.data[i:i + 20]) + '\n')
            dumpfile.write(a2x(self.footer) + '\n')

    def toBase64(self):
        return base64.b64encode(a2s(self.data + self.footer, False))
