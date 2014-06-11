import unittest

import galileo.dongle
from galileo.dongle import isStatus, FitBitDongle

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

class MyDev(object):
    """ Minimal object to reproduce issue#75 """
    def is_kernel_driver_active(self, a): raise NotImplementedError()
    def get_active_configuration(self): return {(0,0): None, (1,0): None}
    def set_configuration(self): pass

class testDongle(unittest.TestCase):

    def testNIE(self):
        def myFind(*args, **kwargs):
            return MyDev()
        galileo.dongle.usb.core.find = myFind
        d = FitBitDongle()
        d.setup()
