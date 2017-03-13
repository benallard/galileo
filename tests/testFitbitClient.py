import unittest

from galileo.tracker import FitbitClient


class MyDM(object):
    def __init__(self, data):
        self.data = data
    def __str__(self): return str(self.data)


class MyCM(object):
    def __init__(self, data):
        self.len = data[0]
        self.INS = data[1]
        self.payload = data[2:]
    def asList(self): return bytearray([self.len, self.INS]) + self.payload
    def __str__(self): return str(self.asList())


class MyDongle(object):
    def __init__(self, responses):
        self.responses = responses
        self.idx = 0
        self.establishLinkEx = False
    def read(self, ctrl):
        response = self.responses[self.idx]
        self.idx += 1
        if not response:
            return None
        if ctrl:
            print(response  )
            return MyCM(bytearray(response))
        else:
            return MyDM(bytearray(response))
    def ctrl_write(self, *args): pass
    def ctrl_read(self, *args):
        return self.read(True)
    def data_read(self, *args):
        return self.read(False)
    def data_write(self, *args): pass
    def setVersion(self, M, m): self.v = (M, m)


class MyDongleWithTimeout(MyDongle):
    """ A Dongle that starts timeouting at threshold """
    def __init__(self, data, threshold):
        MyDongle.__init__(self, data[:threshold] + [()] * (len(data) - threshold))


class MyUUID(object):
    @property
    def int(self): return 0


class MyTracker(object):
    pass


GOOD_SCENARIO = [
    # CancelDiscovery
    (0x20, 1, 0x43, 0x61, 0x6E, 0x63, 0x65, 0x6C, 0x44, 0x69, 0x73, 0x63, 0x6F, 0x76, 0x65, 0x72, 0x79, 0),
    # TerminateLink
    (0x20, 1, 0x54, 0x65, 0x72, 0x6D, 0x69, 0x6E, 0x61, 0x74, 0x65, 0x4C, 0x69, 0x6E, 0x6B, 0),
    (),
    (0x15, 8, 1, 1, 0x6F, 0x7B, 0xAD, 0x29, 0x6A, 0xBC, 0x74, 0x09, 0, 0x20, 0, 0, 0xFF, 0xE7, 3, 0, 1),
    (0x20, 1, 0x53, 0x74, 0x61, 0x72, 0x74, 0x44, 0x69, 0x73, 0x63, 0x6F, 0x76, 0x65, 0x72, 0x79, 0),
    (0x13, 3, 0,0,42,0,0,0, 1, 0x80, 2, 6,4, 0,0,0,0,0,0),
    (3, 2, 1),
    # CancelDiscovery
    (0x20, 1, 0x43, 0x61, 0x6E, 0x63, 0x65, 0x6C, 0x44, 0x69, 0x73, 0x63, 0x6F, 0x76, 0x65, 0x72, 0x79, 0),
    (0x20, 1, 0x45, 0x73, 0x74, 0x61, 0x62, 0x6C, 0x69, 0x73, 0x68, 0x4C, 0x69, 0x6E, 0x6B, 0),
    (3, 4, 0),
    (0x20, 1, 0x47, 0x41, 0x50, 0x5F, 0x4C, 0x49, 0x4E, 0x4B, 0x5F, 0x45, 0x53, 0x54, 0x41, 0x42, 0x4C, 0x49, 0x53, 0x48, 0x45, 0x44, 0x5F, 0x45, 0x56, 0x45, 0x4E, 0x54, 0),
    (2, 7),
    (0xc0, 0xb),
    (8, 6, 6, 0, 0, 0, 0xc8, 0),
    (0xc0, 0x14, 0xc,1, 0,0, 0,0,42,0,0,0),
    # getDump
    (0xc0, 0x41, 0xd),
    (0x26, 2, 0, 0, 0, 0, 0),
    (0xc0, 0,0xd,0x93,0x44,7, 0),
    #response
    (0xc0, 0x12, 4, 0, 0),
    (0xc0, 0x13, 0x14, 0, 0),
    (0xc0, 0x13, 0x24, 0, 0),
    (0xc0, 2),
    (0xc0, 1),
    (0xc0, 0xb),
    (0x20, 1, 0x54, 0x65, 0x72, 0x6D, 0x69, 0x6E, 0x61, 0x74, 0x65, 0x4C, 0x69, 0x6E, 0x6B, 0),
    (3, 5, 0x16, 0),
    (0x20, 1, 0x47, 0x41, 0x50, 0x5F, 0x4C, 0x49, 0x4E, 0x4B, 0x5F, 0x54, 0x45, 0x52, 0x4D, 0x49, 0x4E, 0x41, 0x54, 0x45, 0x44, 0x5F, 0x45, 0x56, 0x45, 0x4E, 0x54, 0),
    (0x20, 1, 0x32, 0x32, 0),
]

SURGE_SCENARIO = [
    (0x16, 0x08, 0x02, 0x05, 0x05, 0xDF, 0x5E, 0x5E, 0xB8, 0xF4, 0x74, 0x04, 0x00, 0x20, 0x00, 0x00, 0xFF, 0xE7, 0x01, 0x00, 0x02, 0x00),
    # CancelDiscovery
    (0x20, 1, 0x43, 0x61, 0x6E, 0x63, 0x65, 0x6C, 0x44, 0x69, 0x73, 0x63, 0x6F, 0x76, 0x65, 0x72, 0x79, 0),
    # TerminateLink
    (0x20, 1, 0x54, 0x65, 0x72, 0x6D, 0x69, 0x6E, 0x61, 0x74, 0x65, 0x4C, 0x69, 0x6E, 0x6B, 0),
    (0x16, 0x08, 0x02, 0x05, 0x05, 0xDF, 0x5E, 0x5E, 0xB8, 0xF4, 0x74, 0x04, 0x00, 0x20, 0x00, 0x00, 0xFF, 0xE7, 0x01, 0x00, 0x02, 0x00),

]


class testScenarii(unittest.TestCase):

    def testOk(self):
        d = MyDongle(GOOD_SCENARIO)
        c = FitbitClient(d)
        self.assertTrue(c.disconnect())
        self.assertTrue(c.getDongleInfo())
        ts = [t for t in c.discover(MyUUID())]
        self.assertEqual(1, len(ts))
        self.assertEqual(ts[0].id, bytearray([0,0,42,0,0,0]))
        self.assertTrue(c.establishLink(ts[0]))
        self.assertTrue(c.toggleTxPipe(True))
        self.assertTrue(c.initializeAirlink(ts[0]))
        dump = c.getDump()
        self.assertFalse(dump is None)
        self.assertEqual(dump.data, bytearray([0x26, 2, 0,0,0,0,0]))
        self.assertTrue(c.uploadResponse((0x26, 2, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)))
        self.assertTrue(c.terminateAirlink())
        self.assertTrue(c.toggleTxPipe(False))
        self.assertTrue(c.ceaseLink())

    def testTimeout(self):
        # the test will have to be re-writen if the scenario changes
        self.assertEqual(28, len(GOOD_SCENARIO))
        for i in range(len(GOOD_SCENARIO) + 1):
            d = MyDongleWithTimeout(GOOD_SCENARIO, i)
            c = FitbitClient(d)
            if i < 1:
                self.assertFalse(c.disconnect(), i)
                continue
            self.assertTrue(c.disconnect())
            if i < 4:
                self.assertFalse(c.getDongleInfo(), i)
                continue
            self.assertTrue(c.getDongleInfo())
            ts = [t for t in c.discover(MyUUID())]
            if i < 6:
                self.assertEqual([], ts, i)
                continue
            self.assertEqual(1, len(ts), i)
            self.assertEqual(ts[0].id, bytearray([0,0,42,0,0,0]))
            if i < 12:
                self.assertFalse(c.establishLink(ts[0]), i)
                continue
            self.assertTrue(c.establishLink(ts[0]), i)
            if i < 13:
                self.assertFalse(c.toggleTxPipe(True), i)
                continue
            self.assertTrue(c.toggleTxPipe(True))
            if i < 15:
                self.assertFalse(c.initializeAirlink(ts[0]))
                continue
            self.assertTrue(c.initializeAirlink(ts[0]))
            if i < 18:
                self.assertEqual(None, c.getDump())
                continue
            dump = c.getDump()
            self.assertFalse(dump is None)
            self.assertEqual(dump.data, bytearray([0x26, 2, 0,0,0,0,0]))
            if i < 22:
                self.assertFalse(c.uploadResponse((0x26, 2, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)))
                continue
            self.assertTrue(c.uploadResponse((0x26, 2, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)))
            if i < 23:
                self.assertFalse(c.terminateAirlink())
                continue
            self.assertTrue(c.terminateAirlink())
            if i < 24:
                self.assertFalse(c.toggleTxPipe(False))
                continue
            self.assertTrue(c.toggleTxPipe(False))
            if i < 28:
                self.assertFalse(c.ceaseLink())
                continue
            self.assertTrue(c.ceaseLink())
            self.assertEqual(len(GOOD_SCENARIO), i)


class testDiscover(unittest.TestCase):

    def testNoTracker(self):
        d = MyDongle([(0x20, 1, 0x53, 0x74, 0x61, 0x72, 0x74, 0x44, 0x69, 0x73, 0x63, 0x6F, 0x76, 0x65, 0x72, 0x79, 0 ),
                      (3, 2, 0),
                      (0x20, 1, 0x43, 0x61, 0x6E, 0x63, 0x65, 0x6C, 0x44, 0x69, 0x73, 0x63, 0x6F, 0x76, 0x65, 0x72, 0x79, 0),
                     ])
        c = FitbitClient(d)
        ts = [t for t in c.discover(MyUUID())]
        self.assertEqual(len(ts), 0)

    def testOnetracker(self):
        d = MyDongle([(0x20, 1, 0x53, 0x74, 0x61, 0x72, 0x74, 0x44, 0x69, 0x73, 0x63, 0x6F, 0x76, 0x65, 0x72, 0x79, 0 ),
                      (0x13, 3, 0xaa,0xaa,0xaa,0xaa,0xaa,0xaa,1,0xe2, 2,6,4, 3,
                       0x2c, 0x31, 0xf6, 0xd8, 0x58),
                      (3, 2, 1),
                      (0x20, 1, 0x43, 0x61, 0x6E, 0x63, 0x65, 0x6C, 0x44, 0x69, 0x73, 0x63, 0x6F, 0x76, 0x65, 0x72, 0x79, 0),
                     ])
        c = FitbitClient(d)
        ts = [t for t in c.discover(MyUUID())]
        self.assertEqual(len(ts), 1)
        t = ts[0]
        self.assertEqual(t.id, bytearray([0xaa] * 6))

    def testTwotracker(self):
        d = MyDongle([(0x20, 1, 0x53, 0x74, 0x61, 0x72, 0x74, 0x44, 0x69, 0x73, 0x63, 0x6F, 0x76, 0x65, 0x72, 0x79, 0 ),
                      (0x13, 3, 0xaa,0xaa,0xaa,0xaa,0xaa,0xaa,1,0xe2, 2,6,4, 3,
                       0x2c, 0x31, 0xf6, 0xd8, 0x58),
                      (0x13, 3, 0xbb,0xbb,0xbb,0xbb,0xbb,0xbb,1,0xe2, 2,6,4, 3,
                       0x2c, 0x31, 0xf6, 0xd8, 0x58),
                      (3, 2, 2),
                      (0x20, 1, 0x43, 0x61, 0x6E, 0x63, 0x65, 0x6C, 0x44, 0x69, 0x73, 0x63, 0x6F, 0x76, 0x65, 0x72, 0x79, 0),
                     ])
        c = FitbitClient(d)
        ts = [t for t in c.discover(MyUUID())]
        self.assertEqual(len(ts), 2)
        t = ts[0]
        self.assertEqual(t.id, bytearray([0xaa] * 6))
        t = ts[1]
        self.assertEqual(t.id, bytearray([0xbb] * 6))

    def testTimeout(self):
        d = MyDongle([(0x20, 1, 0x53, 0x74, 0x61, 0x72, 0x74, 0x44, 0x69, 0x73, 0x63, 0x6F, 0x76, 0x65, 0x72, 0x79, 0 ),
                      (),
                      ()])
        c = FitbitClient(d)
        ts = [t for t in c.discover(MyUUID())]
        self.assertEqual(len(ts), 0)

    def testWrongParams(self):
        """ Sometime, we get the amount before the Status """
        d = MyDongle([(3, 2, 0),
                      (0x20, 1, 0x53, 0x74, 0x61, 0x72, 0x74, 0x44, 0x69, 0x73, 0x63, 0x6F, 0x76, 0x65, 0x72, 0x79, 0 ),
                      (0x20, 1, 0x43, 0x61, 0x6E, 0x63, 0x65, 0x6C, 0x44, 0x69, 0x73, 0x63, 0x6F, 0x76, 0x65, 0x72, 0x79, 0),
                      ])
        c = FitbitClient(d)
        ts = [t for t in c.discover(MyUUID())]
        self.assertEqual(len(ts), 0)

    def testIssue96(self):
        """ Sometime, we don't get payload """
        d = MyDongle([(2, 0xa), ()])
        c = FitbitClient(d)
        ts = [t for t in c.discover(MyUUID())]
        self.assertEqual(len(ts), 0)

    def testIssue231(self):
        """ Some weird Status Messages in the middle """
        d = MyDongle([(0x20, 1, 0x45, 0x52, 0x52, 0x4F, 0x52, 0x3A, 0x20, 0x50, 0x31, 0x5B, 0x37, 0x3A, 0x31, 0x5D, 0x20, 0x73, 0x68, 0x6F, 0x75, 0x6C, 0x64, 0x20, 0x62, 0x65, 0x20, 0x30),
                      (0x20, 1, 0x33),
                      (0x20, 1, 0x53, 0x74, 0x61, 0x72, 0x74, 0x44, 0x69, 0x73, 0x63, 0x6F, 0x76, 0x65, 0x72, 0x79),
                      (0x13, 0x03, 0xD2, 0xCD, 0x91, 0xC1, 0x01, 0xF8, 0x01, 0xB6, 0x02, 0x07, 0x06, 0x3E, 0x00, 0x09, 0x4A, 0x00, 0xFB),
                      (3, 2, 1), ()])
        c = FitbitClient(d)
        ts = [t for t in c.discover(MyUUID())]
        self.assertEqual(len(ts), 1)

class testGetDongleInfo(unittest.TestCase):
    def testIssue136(self):
        d = MyDongle([(0x20, 1, 0x54, 0x65, 0x72, 0x6D, 0x69, 0x6E, 0x61, 0x74, 0x65, 0x4C, 0x69, 0x6E, 0x6B, 0),])
        c = FitbitClient(d)
        self.assertFalse(c.getDongleInfo())

    def testOkOld(self):
        d = MyDongle([(0x15, 8, 1, 1, 0x6F, 0x7B, 0xAD, 0x29, 0x6A, 0xBC, 0x74, 0x09, 0, 0x20, 0, 0, 0xFF, 0xE7, 3, 0, 1),])
        c = FitbitClient(d)
        self.assertTrue(c.getDongleInfo())
        self.assertEqual(d.v, (1,1))
        self.assertEqual(d.flashEraseTime, 2420)
        self.assertEqual(d.firmwareStartAddress, 8192)
        self.assertEqual(d.firmwareEndAddress, 255999)
        self.assertEqual(d.ccIC, 1)

    def testOk(self):
        d = MyDongle([(0x16, 8, 2, 5, 0x71, 0x59, 0x46, 0x16, 0x4A, 0x54, 0x74, 4, 0, 0x20, 0, 0, 0xFF, 0xE7, 1, 0, 2, 0),])
        c = FitbitClient(d)
        self.assertTrue(c.getDongleInfo())
        self.assertEqual(d.v, (2,5))

    def testSurgeDongle(self):
        d = MyDongle([(0x16, 0x08, 0x02, 0x05, 0x05, 0xDF, 0x5E, 0x5E, 0xB8, 0xF4, 0x74, 0x04, 0x00, 0x20, 0x00, 0x00, 0xFF, 0xE7, 0x01, 0x00, 0x02, 0),])
        c = FitbitClient(d)
        self.assertTrue(c.getDongleInfo())
        self.assertEqual(d.v, (2,5))
        self.assertEqual(d.flashEraseTime, 1140)
        self.assertEqual(d.firmwareStartAddress, 8192)
        self.assertEqual(d.firmwareEndAddress, 124927)
        self.assertEqual(d.ccIC, 2)

    def testNewerDongle75(self):
        d = MyDongle([(0x16, 0x08, 0x07, 0x05, 0xA4, 0xA6, 0x69, 0xF3, 0x7B, 0x98, 0x74, 0x04, 0x00, 0x20, 0x00, 0x00, 0xFF, 0xE7, 0x01, 0x00, 0x02, 0x00)])
        c = FitbitClient(d)
        self.assertTrue(c.getDongleInfo())
        self.assertEqual(d.v, (7,5))
        self.assertEqual(d.flashEraseTime, 1140)
        self.assertEqual(d.firmwareStartAddress, 8192)
        self.assertEqual(d.firmwareEndAddress, 124927)
        self.assertEqual(d.ccIC, 2)

class testestablishLink(unittest.TestCase):

    def testestablishLinkExOk(self):
        d = MyDongle([(0x20, 1, 0x45, 0x73, 0x74, 0x61, 0x62, 0x6C, 0x69, 0x73, 0x68, 0x4C, 0x69, 0x6E, 0x6B, 0x45, 0x78, 0x20, 0x63, 0x61, 0x6C, 0x6C, 0x65, 0x64, 0x2E, 0x2E, 0x2E, 0x00),
                      (3, 4, 0),
                      (0x20, 1, 0x47, 0x41, 0x50, 0x5F, 0x4C, 0x49, 0x4E, 0x4B, 0x5F, 0x45, 0x53, 0x54, 0x41, 0x42, 0x4C, 0x49, 0x53, 0x48, 0x45, 0x44, 0x5F, 0x45, 0x56, 0x45, 0x4E, 0x54, 0),
                      (2, 7),])
        d.establishLinkEx = True
        c = FitbitClient(d)
        t = MyTracker()
        t.id = bytearray([0,0,42,0,0,43])
        t.addrType = 1
        self.assertTrue(c.establishLink(t))

    def testestablishLinkExNotOk(self):
        """ When our version test is wrong """
        d = MyDongle([(4, 0xff, 2, 3),
                      (0x20, 1, 0x45, 0x73, 0x74, 0x61, 0x62, 0x6C, 0x69, 0x73, 0x68, 0x4C, 0x69, 0x6E, 0x6B, 0x45, 0x78, 0x20, 0x63, 0x61, 0x6C, 0x6C, 0x65, 0x64, 0x2E, 0x2E, 0x2E, 0),
                      (3, 4, 0),
                      (0x20, 1, 0x47, 0x41, 0x50, 0x5F, 0x4C, 0x49, 0x4E, 0x4B, 0x5F, 0x45, 0x53, 0x54, 0x41, 0x42, 0x4C, 0x49, 0x53, 0x48, 0x45, 0x44, 0x5F, 0x45, 0x56, 0x45, 0x4E, 0x54, 0),
                      (2, 7),])
        d.major = 169; d.minor=78
        c = FitbitClient(d)
        t = MyTracker()
        t.id = bytearray([0,0,42,0,0,43])
        t.addrType = 1
        t.serviceUUID = 0xa005
        self.assertTrue(c.establishLink(t))
        # verify the value is set for later tests
        self.assertTrue(d.establishLinkEx)

class testinitAirLink(unittest.TestCase):

    def testCharge(self):
        d = MyDongle([(8, 6, 6, 0, 0, 0, 0xc8, 0),
                      (0xc0, 0x14, 0xc,0xa, 0,0, 0,0,42,0,0,0, 0x17,0),])
        c = FitbitClient(d)
        t = MyTracker()
        t.id = [0,0,42,0,0,0]
        self.assertTrue(c.initializeAirlink(t))

    def testOthers(self):
        d = MyDongle([(8, 6, 6, 0, 0, 0, 0xc8, 0),
                      (0xc0, 0x14, 0xc,1, 0,0, 0,0,42,0,0,0),])
        c = FitbitClient(d)
        t = MyTracker()
        t.id = [0,0,42,0,0,0]
        self.assertTrue(c.initializeAirlink(t))

    def testEstablishEx(self):
        """ When the dongle uses establishEx, he doesn't read back on the
            ctrl channel """
        d = MyDongle([(0xc0, 0x14, 0xc,1, 0,0, 0,0,42,0,0,0),])
        d.establishLinkEx = True
        c = FitbitClient(d)
        t = MyTracker()
        t.id = [0,0,42,0,0,0]
        self.assertTrue(c.initializeAirlink(t))

class testUpload(unittest.TestCase):

    def testLongMessage(self):
        """ Validate that the seq number rounds up """

        class MyDongle(object):
            def __init__(self, len):
                 self.i = -1
                 self.len = len
            def data_read(self ,*args):
                self.i += 1
                if self.i == 0:
                    return MyDM([0xc0, 0x12, 4, 0, 0])
                if self.i < self.len:
                    return MyDM([0xc0, 0x13, (((self.i) % 16) << 4) + 4, 0, 0])
                return MyDM([0xc0, 2])
            def data_write(self, *args): pass

        d = MyDongle(20)
        c = FitbitClient(d)
        self.assertTrue(c.uploadResponse([0] * 380))


class testDownload(unittest.TestCase):

    def testPreSurge(self):
        d = MyDongle([
            (0xc0, 0x41, 0xd),
            (0x26, 2, 0, 0, 0, 0, 0),
            (0xc0, 0,0xd,0x93,0x44,7, 0)])
        c = FitbitClient(d)
        dump = c.getDump(0xd)
        self.assertTrue(dump.isValid())
        self.assertEqual(dump.data, bytearray([38, 2, 0, 0, 0, 0, 0]))
        self.assertEqual(dump.footer, bytearray([192, 0, 13, 147, 68, 7, 0]))

    def testSurge(self):
        # This is not completely correct
        d = MyDongle([
            (0xc0, 0x41, 0xd, 0x42, 0xa, 0, 0),
            (0x26, 2, 0, 0, 0, 0, 0),
            (0xc0, 0,0xd,0x93,0x44,7, 0)])
        c = FitbitClient(d)
        dump = c.getDump(0xd)
        self.assertTrue(dump.isValid())

class testSetPowerLevel(unittest.TestCase):

    def testOk(self):
        d = MyDongle([(2, 0xfe),])
        c = FitbitClient(d)
        self.assertTrue(c.setPowerLevel(5))
