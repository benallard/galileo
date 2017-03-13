import unittest

from galileo.dump import Dump, TrackerBlock
from galileo.utils import x2a

class testDump(unittest.TestCase):

    def testEmptyNonValid(self):
        d = Dump(6)
        self.assertFalse(d.isValid())

    def testAddIncreasesLen(self):
        d = Dump(5)
        self.assertEqual(d.len, 0)
        d.add(range(10))
        self.assertEqual(d.len, 10)

    def testFooterIsSet(self):
        d = Dump(0)
        self.assertEqual(len(d.footer), 0)
        footer = b'\xc0' + bytearray(range(5))
        d.add(footer)
        self.assertEqual(d.len, 0)
        self.assertEqual(d.footer, footer)

    def testOnlyFooterInvalid(self):
        """ A dump with only a footer is an invalid dump """
        d = Dump(0)
        d.add([0xc0] + list(range(5)))
        self.assertFalse(d.isValid())

    def testEsc1(self):
        d = Dump(0)
        self.assertEqual(d.esc[0], 0)
        d.add([0xdb, 0xdc])
        self.assertEqual(d.len, 1)
        self.assertEqual(d.esc[0], 1)
        self.assertEqual(d.data, b'\xc0')

    def testEsc2(self):
        d = Dump(0)
        self.assertEqual(d.esc[1], 0)
        d.add([0xdb, 0xdd])
        self.assertEqual(d.len, 1)
        self.assertEqual(d.esc[1], 1)
        self.assertEqual(d.data, b'\xdb')

    def testToBase64(self):
        d = Dump(0)
        d.add(range(10))
        d.add([0xc0] + list(range(8)))
        self.assertEqual(d.toBase64(), 'AAECAwQFBgcICcAAAQIDBAUGBw==')

    def testNonValidDataType(self):
        d = Dump(0)
        d.add(range(10))
        d.add([0xc0]+[0, 3])
        self.assertFalse(d.isValid())

    def testNonValidCRC(self):
        d = Dump(0)
        d.add(range(10))
        d.add([0xc0]+[0, 0, 0, 0])
        self.assertFalse(d.isValid())

    def testNonValidLen(self):
        d = Dump(0)
        d.add(range(10))
        d.add([0xc0]+[0, 0, 0x78, 0x23, 0, 0])
        self.assertFalse(d.isValid())

    def testValid(self):
        d = Dump(0)
        d.add(range(10))
        d.add([0xc0]+[0, 0, 0x78, 0x23, 10, 0])
        self.assertTrue(d.isValid())

    def testHugeDump(self):
        # issue 177
        d = Dump(0)
        d.add([5] * 71318)
        d.add([0xc0]+[0, 0, 0x44, 0x95, 0x96, 0x16, 0x01, 0x00])
        self.assertTrue(d.isValid())

    def testDumpProperties(self):
        dump = Dump(13)
        dump.data = bytearray(x2a('2E 02 00 00 01 00 D0 00 00 00 AB CD EF 12 34 56'))

        print(dir(dump))
        self.assertEqual(dump.serial, 'ABCDEF123456')
        self.assertEqual(dump.trackerType, 86)


class testTrackerBlock(unittest.TestCase):

    def testParseProtocolHeader(self):
        block = TrackerBlock()
        block.data = bytearray(x2a('2E 02 00 00 01 00 D0 00 00 00'))

        self.assertEqual(block.megadumpType, '2E')
        self.assertEqual(block.encryption, 1)
        self.assertEqual(block.nonce, bytearray([0xD0, 0x00, 0x00, 0x00]))
