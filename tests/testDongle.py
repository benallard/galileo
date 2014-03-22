import unittest

from galileo.dongle import isStatus

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
