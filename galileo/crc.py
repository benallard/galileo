

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
