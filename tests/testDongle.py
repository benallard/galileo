import unittest

from galileo.dongle import isStatus, CM, DM

class MyCM(object):
    def __init__(self, ins, payload):
        self.INS = ins
        self.payload = payload

class testisStatus(unittest.TestCase):

    def testNotAStatus(self):
        self.assertFalse(isStatus(MyCM(3, [])))

    def testIsaStatus(self):
        self.assertTrue(isStatus(MyCM(1, [])))

    def testEquality(self):
        self.assertTrue(isStatus(MyCM(1, [0x61, 0x62, 0x63, 0x64 , 0]), 'abcd'))

    def testStartsWith(self):
        self.assertTrue(isStatus(MyCM(1, [0x61, 0x62, 0x63, 0x64 , 0]), 'ab'))


class testCM(unittest.TestCase):

    def testEquals(self):
        self.assertTrue(CM(8) == CM(8))
        self.assertTrue(CM(5) == CM(5, []))
        self.assertTrue(CM(2, range(5)), CM(2, range(5)))
        self.assertEquals(CM(8), CM(8))
        self.assertEquals(CM(5), CM(5, []))
        self.assertEquals(CM(2, range(5)), CM(2, range(5)))

    def testNotEquals(self):
        self.assertFalse(CM(7) == CM(8))
        self.assertFalse(CM(9) == CM(9, [5]))
        self.assertFalse(CM(3, range(2)) == CM(3, range(5)))


class testDM(unittest.TestCase):

    def testEquals(self):
        self.assertTrue(DM(range(3)) == DM(range(3)))
        self.assertEquals(DM(range(8)), DM(range(8)))

    def testNotEquals(self):
        self.assertFalse(DM([87]) == DM([42]))
        self.assertFalse(DM(range(2)) == DM(range(5)))
