import unittest

from galileo.config import Config

class MyTracker(object):
    def __init__(self, id, syncedRecently):
        self.id = id
        self.syncedRecently = syncedRecently

class testShouldSkip(unittest.TestCase):

    def testRecentForce(self):
        t = MyTracker([42], True)
        c = Config()
        c.forceSync = True
        self.assertFalse(c.shouldSkip(t))

    def testRecentNotForce(self):
        t = MyTracker([42], True)
        c = Config()
        c.forceSync = False
        self.assertTrue(c.shouldSkip(t))

    def testIncludeNotExclude(self):
        t = MyTracker([0x42], False)
        c = Config()
        c.includeTrackers = ['42']
        self.assertFalse(c.shouldSkip(t))
    def testNotIncludeExclude(self):
        t = MyTracker([0x42], False)
        c = Config()
        c.excludeTrackers = ['42']
        self.assertTrue(c.shouldSkip(t))
    def testIncludeExclude(self):
        t = MyTracker([0x42], False)
        c = Config()
        c.includeTrackers = ['42']
        c.excludeTrackers = ['42']
        self.assertTrue(c.shouldSkip(t))
    def testNotIncludeNotExclude(self):
        t = MyTracker([0x42], False)
        c = Config()
        self.assertFalse(c.shouldSkip(t))
