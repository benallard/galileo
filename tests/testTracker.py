import unittest


from galileo.tracker import Tracker

class testfromDiscovery(unittest.TestCase):

    def testOk(self):
        t = Tracker.fromDiscovery([0xE5, 0x14, 0x53, 0x33, 0xEE, 0xFF, 0x01, 0xBC, 0x02, 0x05, 0x04, 0x03, 0x2C, 0x31, 0xF6, 0xD8, 0x58])
        self.assertEqual(t.id, bytearray([0xE5, 0x14, 0x53, 0x33, 0xEE, 0xFF]))
        self.assertEqual(t.addrType, 1)
        self.assertEqual(t.RSSI, -68)
        self.assertEqual(len(t.serviceData), 2 + 1)
        self.assertEqual(t.serviceData, [5,4,3])
        self.assertEqual(t.serviceUUID, 22744)

    def testSurge(self):
        t = Tracker.fromDiscovery([0xB2, 0x94, 0x82, 0x6E, 0x0C, 0xC8, 0x01, 0xD1, 0x05, 0x10, 0x06, 0xA7, 0x66, 0x03, 0x4A, 0x00, 0xFB])
        self.assertEqual(t.id, bytearray([178,148,130,110,12,200]))
        self.assertEqual(t.addrType, 1)
        self.assertEqual(t.RSSI, -47)
        self.assertEqual(len(t.serviceData), 5 + 1)
        self.assertEqual(t.serviceData, [16,6,167,102,3,74])
        self.assertEqual(t.serviceUUID, 64256)
