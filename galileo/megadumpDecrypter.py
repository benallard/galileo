from .utils import a2msbi, i2msba, a2lsbi, i2lsba
from .xtea import xtea_encrypt

def ba_xor(a, b):
    """ xor between 2 bytearrays """
    assert len(a) == len(b)
    return i2msba(a2msbi(a) ^ a2msbi(b), len(a))

class XTEA_CMAC(object):
    def __init__(self, key, msg=None):
        self.key = key
        self._iv = bytearray(8)

        # we need k1, k2
        Rb = 0x1b # 8 bytes cipher block
        l = xtea_encrypt(key, bytearray(8))
        self.k1 = a2msbi(l) << 1
        if (l[0] & 0x80):
            self.k1 ^= Rb
        self.k2 = self.k1 << 1
        if i2msba(self.k1, 8)[0] & 0x80:
            self.k2 ^= Rb

        # Reduce to 8 bytes
        self.k1 = self.k1 % 2**64
        self.k2 = self.k2 % 2**64

        self._msg = bytearray()
        if msg is not None:
            self.update(msg)

    def update(self, block):
        """ Add some blocks to the current calculation """
        self._msg.extend(block)
        # Process the complete blocks
        while len(self._msg) > 8:
            block = self._msg[:8]
            self._msg = self._msg[8:]
            self._iv = ba_xor(self._iv, block)
            self._iv = xtea_encrypt(self.key, self._iv)

    def digest(self):
        """ Returns the current MAC """
        # Process the remaining part
        if len(self._msg) == 8:
            # XOR with k1
            block = i2msba(self.k1 ^ a2msbi(self._msg), 8)
        else:
            # Add padding
            block = self._msg
            block.append(0x80)
            block.extend(bytearray(8-len(self._msg)))
            # XOR with k2
            block = i2msba(a2msbi(block) ^ self.k2, 8)

        return xtea_encrypt(self.key, ba_xor(self._iv, block))
    final = digest


def counter(nonce):
    """ A simple counter for the CTR Cipher """
    width = len(nonce)
    value = a2lsbi(nonce)
    while True:
        value = (value + 1) % 2**(8*width)
        yield bytearray(i2lsba(value, width))


def computeCounter(key, nonce):
    emptyBlock = bytearray(8)
    cmac = XTEA_CMAC(key)
    cmac.update(emptyBlock)
    cmac.update(nonce)
    counter = cmac.final()
    return counter


class XTEA_CTR(object):
    def __init__(self, key, nonce):
        self.key = key
        self.counter = counter(nonce)

    def _keygen(self):
        while True:
            for k in xtea_encrypt(self.key, next(self.counter)):
                yield k

    def decrypt(self, data):
        return [ x ^ y for (x,y) in zip(data,self._keygen) ]


def decrypt(dump, key, offset=16):
    counter = computeCounter(key, dump.nonce)
    cipher = XTEA_CTR(key, nonce=counter)
    decryptedData = cipher.decrypt(dump.data[offset:])
    dump.data[offset:]= decryptedData
    return dump
