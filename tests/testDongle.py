import unittest

from galileo.dongle import isStatus

class testisStatus(unittest.TestCase):

    def testNotAStatus(self):
        self.assertFalse(isStatus([2, 3]))

    def testIsaStatus(self):
        self.assertTrue(isStatus([32, 1]))

    def testEquality(self):
        self.assertTrue(isStatus([32, 1, 0x61, 0x62, 0x63, 0x64 , 0]), 'abcd')

    def testStartsWith(self):
        self.assertTrue(isStatus([32, 1, 0x61, 0x62, 0x63, 0x64 , 0]), 'ab')
