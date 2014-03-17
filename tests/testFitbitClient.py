import unittest

from galileo.tracker import FitbitClient, TimeoutError

class MyDM(object):
    def __init__(self, data):
        self.data = data

class MyDongle(object):
    def __init__(self, responses):
        self.responses = responses
        self.idx = 0
    def read(self, *args):
        response = self.responses[self.idx]
        self.idx += 1
        if not response:
            raise TimeoutError
        return list(response)
    def ctrl_write(self, *args): pass
    ctrl_read = read
    def data_read(self, *args):
        return MyDM(self.read())
    def data_write(self, *args): pass

class MyUUID(object):
    @property
    def int(self): return 0

class testScenarii(unittest.TestCase):

    def testOk(self):
        d = MyDongle([(0x20, 1), # CancelDiscovery
                      (0x20, 1), # TerminateLink
                      (),
                      (0x15, 8, 1, 1),
                      (0x20, 1), # StartDiscovery
                      (0x13, 3, 0,0,42,0,0,0, 1, 0x80, 2, 6,4),
                      (3, 2, 1),
                      (0x20, 1), # cancelDiscovery
                      (0x20, 1), # EstablishLink
                      (3, 4),
                      (0x20, 1), #GAP_LINK_ESTABLISHED_EVENT
                      (2, 7),
                      (0xc0, 0xb),
                      (8, 6, 6, 0, 0, 0, 0xc8, 0),
                      (0xc0, 0x14, 0xc, 1, 0, 0, 0,0,0,0,0,0),
                      # getDump
                      (0xc0, 0x41, 0xd),
                      (0x26, 2, 0, 0, 0, 0, 0),
                      (0xc0, 0,0,0,0,0),
                      #response
                      (0xc0, 0x12, 4, 0, 0),
                      (0xc0, 0x13, 0x14, 0, 0),
                      (0xc0, 0x13, 0x24, 0, 0),
                      (0xc0, 2),
                      (0xc0, 1),
                      (0xc0, 0xb),
                      (0x20, 1), # TerminateLink
                      (3, 5, 0x16, 0),
                      (0x20, 1), # GAP_LINK_TERMINATED_EVENT
                      (0x20, 1), #22
                     ])
        c = FitbitClient(d)
        c.disconnect()
        c.getDongleInfo()
        ts = [t for t in c.discover(MyUUID())]
        self.assertEqual(1, len(ts))
        self.assertEqual(ts[0].id, [0,0,42,0,0,0])
        c.establishLink(ts[0]),
        c.enableTxPipe()
        c.initializeAirlink()
        dump = c.getDump()
        self.assertEqual(dump.data, [0x26, 2, 0,0,0,0,0])
        c.uploadResponse((0x26, 2, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0))
        c.disableTxPipe()
        c.terminateAirlink()

class testDiscover(unittest.TestCase):

    def testNoTracker(self):
        d = MyDongle([(0x20, 1 ), # StartDiscovery
                      (3, 2, 0),
                      (0x20, 1, ) # CancelDiscovery
                     ])
        c = FitbitClient(d)
        ts = [t for t in c.discover(MyUUID())]
        self.assertEqual(len(ts), 0)

    def testOnetracker(self):
        d = MyDongle([(0x20, 1 ), # StartDiscovery
                      (0x13, 3, 0xaa,0xaa,0xaa,0xaa,0xaa,0xaa,1,-30, 2,6,4, 3,
                       0x2c, 0x31, 0xf6, 0xd8, 0x58),
                      (3, 2, 1),
                      (0x20, 1, ) # CancelDiscovery
                     ])
        c = FitbitClient(d)
        ts = [t for t in c.discover(MyUUID())]
        self.assertEqual(len(ts), 1)
        t = ts[0]
        self.assertEqual(t.id, [0xaa] * 6)

    def testTwotracker(self):
        d = MyDongle([(0x20, 1 ), # StartDiscovery
                      (0x13, 3, 0xaa,0xaa,0xaa,0xaa,0xaa,0xaa,1,-30, 2,6,4, 3,
                       0x2c, 0x31, 0xf6, 0xd8, 0x58),
                      (0x13, 3, 0xbb,0xbb,0xbb,0xbb,0xbb,0xbb,1,-30, 2,6,4, 3,
                       0x2c, 0x31, 0xf6, 0xd8, 0x58),
                      (3, 2, 2),
                      (0x20, 1, ) # CancelDiscovery
                     ])
        c = FitbitClient(d)
        ts = [t for t in c.discover(MyUUID())]
        self.assertEqual(len(ts), 2)
        t = ts[0]
        self.assertEqual(t.id, [0xaa] * 6)
        t = ts[1]
        self.assertEqual(t.id, [0xbb] * 6)

    def testTimeout(self):
        d = MyDongle([(0x20, 1 ), # StartDiscovery
                      (),
                      ()])
        c = FitbitClient(d)
        with self.assertRaises(TimeoutError):
            ts = [t for t in c.discover(MyUUID())]
            self.assertEqual(len(ts), 0)

    def testWrongParams(self):
        # Sometime, we get the amount before the Status
        d = MyDongle([(3, 2, 0),
                      (0x20, 1 ), # StartDiscovery
                      (0x20, 1, ) # CancelDiscovery
                     ])
        c = FitbitClient(d)
        ts = [t for t in c.discover(MyUUID())]
        self.assertEqual(len(ts), 0)
