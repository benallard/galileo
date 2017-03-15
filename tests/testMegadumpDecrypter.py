import unittest

from galileo.megadumpDecrypter import computeCounter, counter
from galileo.utils import x2a

class TestXTEAMegadumpDecrypter(unittest.TestCase):

    def testComputeCounter(self):
        key = bytearray([
            0x12, 0x34, 0x56, 0x78,
            0x12, 0x34, 0x56, 0x78,
            0x12, 0x34, 0x56, 0x78,
            0x12, 0x34, 0x56, 0x78
            ])

        nonce = bytearray([0xDE, 0xAD, 0xBE, 0xEF])

        counter = computeCounter(key, nonce)
        self.assertEqual(counter, bytearray(x2a('a9 3f 69 fc 60 eb 75 25')))

class testCounter(unittest.TestCase):
    def testSimple(self):
        c = counter(bytearray('$2dUI84e', 'utf-8'))
        self.assertEqual(bytearray(r'%2dUI84e', 'utf-8'), next(c))
        self.assertEqual(bytearray(r'&2dUI84e', 'utf-8'), next(c))
        self.assertEqual(bytearray(r"'2dUI84e", 'utf-8'), next(c))
