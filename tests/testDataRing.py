import unittest

from galileo.dongle import DataRing

class testRing(unittest.TestCase):
    def testEmpty(self):
        r = DataRing(5)
        self.assertEquals([], r.getData())
        self.assertTrue(r.empty)
        self.assertFalse(r.full)

    def testCapaNull(self):
        r = DataRing(0)
        r.add(5)
        self.assertEquals([], r.getData())
        self.assertTrue(r.empty)
        self.assertTrue(r.full)

    def testOneElement(self):
        r = DataRing(10)
        r.add('data')
        self.assertEquals(['data'], r.getData())
        self.assertFalse(r.empty)
        self.assertFalse(r.full)
        self.assertEquals(r.queue + 1, r.head)
        self.assertEquals(1, r.fill)

    def testTwoElement(self):
        r = DataRing(10)
        r.add('data1')
        r.add('data2')
        self.assertFalse(r.empty)
        self.assertEquals(['data1', 'data2'], r.getData())
        self.assertEquals(2, r.fill)

    def testThreeElement(self):
        r = DataRing(10)
        r.add('data1')
        r.add('data2')
        r.add('data3')
        self.assertFalse(r.empty)
        self.assertEquals(['data1', 'data2', 'data3'], r.getData())
        self.assertEquals(3, r.fill)

    def testOverflow(self):
        r = DataRing(2)
        self.assertFalse(r.full)
        self.assertEquals(0, r.fill)
        r.add('data1')
        self.assertFalse(r.full)
        self.assertEquals(1, r.fill)
        r.add('data2')
        self.assertTrue(r.full)
        self.assertEquals(2, r.fill)
        r.add('data3')
        self.assertFalse(r.empty)
        self.assertTrue(r.full)
        self.assertEquals(2, r.fill)
        self.assertEquals(['data2', 'data3'], r.getData())
