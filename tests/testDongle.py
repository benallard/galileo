import errno
import unittest

import galileo.dongle
from galileo.dongle import isStatus, FitBitDongle, isATimeout
USBError = galileo.dongle.usb.core.USBError

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

class testisATimeout(unittest.TestCase):

    def testErrnoTIMEOUT(self):
        """ usb.core.USBError: [Errno 110] Operation timed out """
        self.assertTrue(isATimeout(USBError('Operation timed out', errno=errno.ETIMEDOUT)))

    def testpyusb1a2(self):
        """\
        issue#17
        usb.core.USBError: Operation timed out """
        self.assertTrue(isATimeout(IOError('Operation timed out')))

    def testlibusb0(self):
        """\
        issue#82
        usb.core.USBError: [Errno None] Connection timed out """
        self.assertTrue(isATimeout(USBError('Connection timed out')))
